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
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)