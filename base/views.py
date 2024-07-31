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
from .models import Cart, Products, Order
from .form import AddProduct


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

def generate_pdf(order):
    # Path to save the PDF
    pdf_path = f"order_{order.order_id}.pdf"
    full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)  # Save to media directory

    # Company details
    company_name = "Flipkart"
    gst_number = "1234327tfc3"
    pan_number = "PSGW8545G"

    # Create a PDF with ReportLab
    c = canvas.Canvas(full_pdf_path, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, height - 1 * inch, company_name)
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 1.25 * inch, f"GST Number: {gst_number}")
    c.drawString(1 * inch, height - 1.5 * inch, f"PAN Number: {pan_number}")

    # Invoice details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, height - 2 * inch, f"Order ID: {order.order_id}")
    c.drawString(1 * inch, height - 2.25 * inch, f"Total Amount: ₹{order.total_amount}")

    # Date
    from datetime import datetime
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 2.5 * inch, f"Date: {datetime.now().strftime('%Y-%m-%d')}")

    # Add more details if needed

    c.save()

    return pdf_path

def download_receipt(request):
    order_id = request.GET.get('order_id')
    order = get_object_or_404(Order, order_id=order_id)
    pdf_path = generate_pdf(order)

    full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    return FileResponse(open(full_pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=f"receipt_{order_id}.pdf")

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
    return render(request, 'home.html', {'items': items})

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
        cart_product = Cart.objects.get(product=cart_item, user=user)
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
    cart_items = Cart.objects.filter(user=request.user)
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
            data = json.loads(request.body)
            razorpay_payment_id = data['razorpay_payment_id']
            razorpay_order_id = data['razorpay_order_id']
            razorpay_signature = data['razorpay_signature']

            # Verify payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            # Assume `cart` is fetched based on some logic, e.g., from session or user
            cart_items = Cart.objects.filter(user=request.user)  # Replace with your method to get the cart
            totalamt = sum(i.total for i in cart_items)

            # Save order details
            order = Order.objects.create(
                order_id=razorpay_order_id,
                total_amount=totalamt   # Convert back to rupees
            )

            # Generate PDF receipt
            pdf_path = generate_pdf(order)
            cart_items.delete()

            return JsonResponse({'status': 'success', 'pdf_url': pdf_path})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)




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
