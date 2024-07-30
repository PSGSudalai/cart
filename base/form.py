from django import forms

from base.models import Products

class AddProduct(forms.ModelForm):
    class Meta:
        model=Products
        fields=['item','price','image']