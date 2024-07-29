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

def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

def is_razorpay_payment_order_successful(order_id):
    order_response = get_razorpay_client().order.fetch(order_id=order_id)
    return order_response.get("status") in ["paid"]

def create_razorpay_payment_order(amount, currency, receipt):
    return get_razorpay_client().order.create(
        data={"amount": int(amount) * 100, "currency": currency, "receipt": receipt}
    )

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
            data = json.loads(request.body)
            order_id = data.get("order_id")

            if is_razorpay_payment_order_successful(order_id):
                return JsonResponse({"status": "success", "order_id": order_id})
            else:
                raise ValidationError("Payment verification failed")
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

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
    return generate_pdf_receipt(order_id)

def payment_form(request):
    return render(request, 'index.html', {'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID})


# Create your views here.

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

        elif password1 == password2:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=firstname,
                last_name=lastname
            )
        login(request,user)
        messages.success(request, 'Registration successful')
        return redirect('home')
    else:
        messages.error(request, 'Passwords do not match. Please try again.')

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
            return redirect('Signin')

    return render(request, 'login.html')

def Signout(request):
    logout(request)
    return redirect('home')

def home(request):
    return render(request,'home.html')