from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse, FileResponse
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import razorpay
import json
from django.conf import settings
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from requests import request
from .models import Cart, Products, Order
from .form import AddProduct
from weasyprint import HTML
from datetime import datetime, timedelta
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware
import openpyxl
from base.models import Cart
from django.core.mail import EmailMessage
from io import BytesIO
from django.utils.timezone import now 
import logging


# import pdfkit



def register(request):
    if request.method == 'POST':
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Please choose another username.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email address is already in use. Please use another email.')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match. Please try again.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=firstname,
                last_name=lastname
            )
            user.save()
            login(request, user)
            messages.success(request, 'Registration successful')
            return redirect('home')
    return render(request, 'register.html')

def Signin(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid Username or Password")
            return redirect('signin')
    return render(request, 'login.html')

def Signout(request):
    logout(request)
    return redirect('home')

def home(request):
    items = Products.objects.all()
    cart_count = 0
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user,is_sold=False).count()

    return render(request, 'home.html', {'items': items, 'count': cart_count})


@login_required(login_url='signin')
def item(request):
    if request.method == 'POST':
        form = AddProduct(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request,'Product created successfully!')
            return redirect('home')
    else:
        form = AddProduct()
    context = {'form': form}
    return render(request, 'item_cart.html', context)

@login_required(login_url='signin')

def cart(request, pk):
    cart_item = get_object_or_404(Products, id=pk)
    user = request.user
    quantity = int(request.POST.get('quantity', 1))
    price = cart_item.price
    total = price * quantity  # Calculate total price based on quantity

    try:
        cart_product = Cart.objects.get(product=cart_item, user=user , is_sold=False)
        cart_product.quantity += quantity
        cart_product.total = cart_product.price * cart_product.quantity
        cart_product.save()
        messages.success(request, f'Updated {cart_item.item} quantity to {cart_product.quantity}.')
    except Cart.DoesNotExist:
        Cart.objects.create(product=cart_item, user=user, price=price, quantity=quantity, total=total)
        messages.success(request, f'Added {cart_item.item} to your cart.')

    return redirect('home')

def delete(request, pk):
    cart = Cart.objects.get(id=pk)
    cart.delete()
    return redirect('cart-view')
def back(request):
    return redirect('home')

@login_required(login_url='signin')
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user,is_sold=False)
    cart_total = 0
    for i in cart_items:
        cart_total += i.total
    context = {'cart_items': cart_items, 'cart_total': cart_total}
    return render(request, 'cart.html', context)

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

@csrf_exempt
def create_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')  # Amount in paise
            currency = 'INR'

            # Create an order on Razorpay
            razorpay_order = client.order.create(dict(amount=amount, currency=currency, payment_capture='0'))

            # Save order details in your database if necessary
            order_id = razorpay_order['id']

            return JsonResponse({
                'order_id': order_id,
                'razorpay_key': settings.RAZORPAY_KEY_ID,
                'amount': amount
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def verify_payment(request):
    if request.method == 'POST':
        try:
            # Load data from request body
            data = json.loads(request.body)
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')

            # Check for missing payment details
            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                return JsonResponse({'error': 'Missing payment details'}, status=400)

            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

            # Verify payment signature
            try:
                client.utility.verify_payment_signature({
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                })
            except razorpay.errors.SignatureVerificationError:
                return JsonResponse({'error': 'Payment signature verification failed'}, status=400)

            # Fetch cart items
            items = Cart.objects.filter(user=request.user, is_sold=False)
            cart_items = Cart.objects.filter(user=request.user, is_sold=False)

            if not cart_items.exists():
                return JsonResponse({'error': 'No items in cart'}, status=400)

            # Calculate total amount
            totalamt = sum(item.total for item in cart_items)

            # Save order details
            order = Order.objects.create(
                order_id=razorpay_order_id,
                total_amount=totalamt,
                user=request.user,
                 # Assuming your Order model has a user field
            )
            order.items.set(cart_items)
            
            # Mark cart items as sold
            items.update(is_sold=True)
            # Generate PDF receipt
            pdf_path = generate_pdf(request, order, cart_items)
            # download_receipt(request, order, items)

            

            return JsonResponse({'status': 'success', 'pdf_url': pdf_path, 'order_id': order.order_id})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except KeyError as e:
            return JsonResponse({'error': f'Missing key: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))


def generate_pdf(request, order, cart_items):
    # Path to save the PDF
    pdf_path = f"order_{order.order_id}.pdf"
    full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)  # Save to media directory

    # Fetch the cart items for the given user and pk
    

    # HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ font-weight: bold; font-size: 14pt; text-align: center; }}
            .date {{ font-size:12pt; margin-left:300px;}}
            .total {{ font-size:12pt; margin-left:400px;}}
            .details {{ font-size: 12pt; }}
            .bio {{ font-size: 12pt; margin-right: 100px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
            .table {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">Shopping Market</div>
        <div class="date"> <p>Date: {datetime.now().strftime('%d-%m-%Y')}</p>
            <p>Order ID: {order.order_id}</p></div>
        <div class="details">
            <p>Name: {request.user.username}</p>
            <p>Address: xyz, Chennai</p>
        </div>
        <div class="table">
            <table>
                <tr>
                    <th>Item</th>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Total</th>
                </tr>"""
    
    # Add cart items to the HTML content
    for item in cart_items:
        html_content += f"""
                <tr>
                    <td>{item.product.item}</td>
                    <td>₹{item.price}</td>
                    <td>{item.quantity}</td>
                    <td>₹{item.price * item.quantity}</td>
                </tr>"""

    # Close the table and add the order summary
    html_content += f"""
            </table>
        </div>
        <div class="total"><p>Total Amount: ₹{order.total_amount}</p></div
        <div class="bio">
            <p>GST Number: 12d567hh</p>
            <p>PAN Number: PSDF7657H</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF
    HTML(string=html_content).write_pdf(full_pdf_path)

    return full_pdf_path

# def download_receipt(request, order, items):
#     pdf_path = generate_pdf(request, order, items)
#     full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    
#     # Ensure the file exists
#     if os.path.exists(full_pdf_path):
#         return FileResponse(open(full_pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=f"receipt_{order.order_id}.pdf")
#     else:
#         return JsonResponse({'error': 'File not found'}, status=404)



def download_receipt(request):
    order_id = request.GET.get('order_id')
    order = get_object_or_404(Order, order_id=order_id)
    cart_items = Cart.objects.filter(user=request.user,is_sold=True)
    pdf_path = generate_pdf(request, order, cart_items)
    full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    return FileResponse(open(full_pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=f"receipt_{order_id}.pdf")


@require_POST
def update_quantity(request, pk):
    cart_item = get_object_or_404(Cart, id=pk)
    action = request.POST.get('action')

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1
    cart_item.total = cart_item.quantity* cart_item.price
    cart_item.save()
    return redirect('cart-view')


def profile(request):
    today = datetime.now().date()
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        start_date = parse_date(start_date)
    if end_date:
        end_date = parse_date(end_date)
    # items = Order.objects.all()
    # for item in items:
    #     item.items
    #     for sub_item in item.items.all():
    #         sub_item.items

    cart_count = Cart.objects.filter(user=request.user, is_sold=True).count()
    amt = Cart.objects.filter(user=request.user, is_sold=True)
    orders=Order.objects.filter(user=request.user)
    item=Order.objects.all()
    for order in orders:
        order.order_id
        order.created
    
    if start_date and end_date:
        amt = amt.filter(created__date__range=[start_date, end_date])
    elif start_date:
        amt = amt.filter(created__date__gte=start_date)
    elif end_date:
        amt = amt.filter(created__date__lte=end_date)
    
    value = sum(item.total for item in amt)
    
    context = {
        'cart': cart_count,
        'amt': amt,
        'value': value,
        'start_date': start_date,
        'end_date': end_date,
        'orders':orders,
        'item':item
        
    }
    return render(request, 'order.html', context)



def generate_report(request):
    report_detail = Cart.objects.filter(
        is_sold=True, 
        
    )

    # Aggregate data by product
    product_data = {}
    for item in report_detail:
        product_name = item.product.item  # Assuming there's a field 'product_name'
        if product_name not in product_data:
            product_data[product_name] = {'quantity': 0, 'total': 0}
        product_data[product_name]['quantity'] += 1  # Increment quantity
        product_data[product_name]['total'] += item.price  # Assuming 'price' is the total price of the item

    # Create Excel workbook
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sales Report"

    # Set header
    sheet['A1'] = 'Product'
    sheet['B1'] = 'Quantity'
    sheet['C1'] = 'Total Price'

    # Populate the sheet with data
    row = 2
    for product_name, data in product_data.items():
        sheet[f'A{row}'] = product_name
        sheet[f'B{row}'] = data['quantity']
        sheet[f'C{row}'] = data['total']
        row += 1


    file_stream = BytesIO()
    workbook.save(file_stream)
    file_stream.seek(0)
    
    response = HttpResponse(file_stream, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
    
    return response

logger = logging.getLogger(__name__)

def pdf(cart_items, order, username):
    try:
        # Generate the PDF logic as before
        pdf_filename = f"order_{order.order_id}.pdf"
        full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_filename)

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ font-weight: bold; font-size: 14pt; text-align: center; }}
                .date {{ font-size:12pt; text-align: right; }}            
                .total {{ font-size:12pt; margin-left:400px;}}
                .details {{ font-size: 12pt; margin-top: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="header">Shopping Market</div>
            <div class="date">Date: {now().strftime('%Y-%m-%d')}</div>
            <div class="details">
                <p>Name: {username}</p>
                <p>Address: xyz, Chennai</p>
            </div>
            <table>
                <tr>
                    <th>Item</th>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Total</th>
                </tr>"""

        for item in cart_items:
            html_content += f"""
                <tr>
                    <td>{item.product.item}</td>
                    <td>₹{item.price}</td>
                    <td>{item.quantity}</td>
                    <td>₹{item.price * item.quantity}</td>
                </tr>"""

        html_content += """
            </table>
            <div class="bio">
                <p>GST Number: 12d567hh</p>
                <p>PAN Number: PSDF7657H</p>
            </div>
        </body>
        </html>
        """

        HTML(string=html_content).write_pdf(full_pdf_path)
        return pdf_filename
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return None

def download(request, order_id):
    try:
        order = get_object_or_404(Order, pk=order_id, user=request.user)
        cart_items = Cart.objects.filter(order=order, is_sold=True)

        if not cart_items:
            raise Http404("No cart items found for this order.")

        pdf_filename = pdf(cart_items, order, request.user.username)
        if not pdf_filename:
            raise Http404("Error generating PDF file.")

        full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_filename)

        if not os.path.exists(full_pdf_path):
            raise Http404("PDF file not found.")

        return FileResponse(open(full_pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=pdf_filename)
    except Exception as e:
        logger.error(f"Error in download view: {e}")
        raise Http404("Error processing download request.")

    
def generate(request, cart_items):
    # Path to save the PDF
    pdf_path = f"order_date.pdf"
    full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)

    # HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ font-weight: bold; font-size: 14pt; text-align: center; }}
            .date {{ font-size:12pt; margin-left:400px;}}
            .details {{ font-size: 12pt; }}
            .bio {{ font-size: 12pt; margin-right: 100px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
            .table {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">Shopping Market</div>
        <div class="date"> <p>Date: {datetime.now().strftime('%Y-%m-%d')}</p></div>
        <div class="details">
            <p>Name: {request.user.username}</p>
            <p>Address: xyz, Chennai</p>
        </div>
        <div class="table">
            <table>
                <tr>
                    <th>Item</th>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Total</th>
                </tr>"""

    # Add cart items to the HTML content
    for item in cart_items:
        html_content += f"""
                <tr>
                    <td>{item.product.item}</td>
                    <td>₹{item.price}</td>
                    <td>{item.quantity}</td>
                    <td>₹{item.price * item.quantity}</td>
                </tr>"""

    # Close the table and add the order summary
    html_content += f"""
            </table>
        </div>
        <div class="bio">
            <p>GST Number: 12d567hh</p>
            <p>PAN Number: PSDF7657H</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF
    HTML(string=html_content).write_pdf(full_pdf_path)

    return full_pdf_path



def receipt(request, from_date):
    # Convert from_date string to a datetime object
    from_date = datetime.strptime(from_date, '%Y-%m-%d')
    from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Set end_date to the end of the same day
    end_date = from_date + timedelta(days=1) - timedelta(microseconds=1)

    # Filter cart items by the specified date range
    cart_items = Cart.objects.filter(
        user=request.user,
        is_sold=True,
        created__range=(from_date, end_date)
    )

    # Generate the PDF
    pdf_path = generate(request, cart_items)  # Adjust if `order` is needed

    # Serve the generated PDF as a response
    full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    return FileResponse(open(full_pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=f"receipt_{from_date.strftime('%Y-%m-%d')}.pdf")