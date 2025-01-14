from django.conf import settings
from . import views
from django.urls import path
from django.conf.urls.static import static

urlpatterns = [
    path('register/', views.register, name='register'),
    path('signin/', views.Signin, name='signin'),
    path('signout/', views.Signout, name='signout'),
    path('', views.home, name='home'),
    path('item/', views.item, name='item'), 
    # path('item/<int:product_id>/',views.item, name='edit_product'),
    path('cart/<int:pk>/', views.cart, name='cart'),
    path('delete_item/<int:item_id>/', views.delete_item, name='delete_item'),
    path('delete/<int:pk>/', views.delete, name='delete'),
    path('cart-view/', views.cart_view, name='cart-view'),
    path('create_order/', views.create_order, name='create_order'),
    path('verify/', views.verify_payment, name='verify'),
    path('update_quantity/<int:pk>/', views.update_quantity, name='update_quantity'),
    path('download-receipt/', views.download_receipt, name='download_receipt'),
    path('receipt/<str:from_date>/', views.receipt, name='receipt'),
    path('download/<int:order_id>/', views.download, name='download'),
    path('back/', views.back, name='back'),
    path('profile/', views.profile, name='profile'),
    path('report/', views.generate_report, name='report'),
   
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)