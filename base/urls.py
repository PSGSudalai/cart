from django.conf import settings
from . import views
from django.urls import path
from django.conf.urls.static import static

urlpatterns = [
    path('',views.home,name='home'),
    path('register/',views.register,name='register'),
    path('Signin/',views.Signin,name='signin'),
    path('signout/',views.Signout,name='signout'),
    path('item/',views.item,name='item'),
    path('cart/<int:pk>/',views.cart,name='cart'),
    path('cart-view/', views.cart_view, name='cart-view'),
    path('verify-payment/', views.verify_payment, name='verify'),
    path('create-order/', views.create_order, name='create_order'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)