from . import views
from django.urls import path

urlpatterns = [
    path('',views.home,name='home'),
    path('register/',views.register,name='register'),
    path('Signin/',views.Signin,name='signin'),
    path('signout/',views.Signout,name='signout'),
]