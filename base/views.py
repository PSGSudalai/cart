from django.shortcuts import render,redirect
import json
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.views import View
import razorpay
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import io
from django.contrib.auth.decorators import login_required
from base.form import AddProduct
from base.models import Cart, Products
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from .models import Order 


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

def is_razorpay_payment_order_successful(order_id):
    order_response = get_razorpay_client().order.fetch(order_id=order_id)
    return order_response.get("status") in ["paid"]

def create_razorpay_payment_order(amount, currency, receipt):
    return get_razorpay_client().order.create(
        data={"amount": int(amount) * 100, "currency": currency, "receipt": receipt}
    )

@login_required(login_url='signin')
class CreateOrderView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            amount = data.get("amount")
            currency = data.get("currency", "INR")
            receipt = data.get("receipt")

            order = create_razorpay_payment_order(amount, currency, receipt)
            return JsonResponse(order)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


class VerifyPaymentView(View):
    def post(self, request, *args, **kwargs):
        try:
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')

            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

            # Fetch order details from Razorpay
            order = client.order.fetch(razorpay_order_id)

            # Verify the payment signature
            generated_signature = client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            if generated_signature:
                # Payment is verified
                return JsonResponse({"status": "success", "order_id": razorpay_order_id})
            else:
                # Payment verification failed
                raise ValidationError("Payment verification failed")

        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except razorpay.errors.RazorpayError as e:
            # Handle Razorpay-specific errors
            return JsonResponse({"error": "Razorpay error: " + str(e)}, status=400)
        except Exception as e:
            # Handle general errors
            return JsonResponse({"error": "An unexpected error occurred: " + str(e)}, status=500)
        


def generate_pdf_receipt(order_id):
    order_details = get_razorpay_client().order.fetch(order_id=order_id)
    template = get_template('receipt.html')
    html = template.render({'order': order_details})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{order_id}.pdf"'

    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), dest=response)
    if pisa_status.err:
        return HttpResponse(f'We had some errors with code {pisa_status.err} <pre>{html}</pre>')
    return response

def download_receipt(request):
    order_id = request.GET.get('order_id')
    order = get_object_or_404(Order, order_id=order_id)
    receipt_content = f"Receipt for Order ID: {order.order_id}\nTotal Amount: {order.total_amount}"

    response = HttpResponse(receipt_content, content_type='application/text')
    response['Content-Disposition'] = f'attachment; filename="receipt_{order_id}.txt"'
    
    return response


def payment_form(request):
    return render(request, 'index.html', {'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID})



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
            messages.error(request, "Invalid UserName or Password")
            return redirect('signin')

    return render(request, 'login.html')

def Signout(request):
    print(request.user)
    print(request.user.username)
    breakpoint()

    logout(request)
    return redirect('home')

def home(request):
    items = Products.objects.all()
    return render(request, 'home.html', {'items': items})



@login_required(login_url='signin')
def item(request):
    if request.method == 'POST':
        form = AddProduct(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = AddProduct()

    context = {'form': form}
    return render(request, 'item_cart.html', context)


def cart(request,pk):
    product=Products.objects.get(id=pk)
    user=request.user
    price=product.price
    Cart.objects.create(product=product,user=user,price=price, quantity =1)
    return render(request,'cart.html')

@login_required(login_url='signin')
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user)
    return render(request, 'cart.html', {'cart_items': cart_items})


client = razorpay.Client(auth=("rzp_test_sYDXizFjDxb4Vw", "mWbFEV0lUB2Mzp71x57wZSw2"))


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

            # Save order details
            order = Order.objects.create(
                order_id=razorpay_order_id,
                total_amount=100 / 100  # Convert back to rupees
            )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)
