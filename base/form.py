from django import forms

from base.models import Item

class AddToCart(forms.ModelForm):
    class Meta:
        model=Item
        fields=['item','price']