from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Products(models.Model):
    item=models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2) 

    def __str__(self):
        return self.item
    
class Cart(models.Model):
    product=models.ForeignKey(Products, on_delete=models.CASCADE)
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    price=models.IntegerField()
  
    def __str__(self):
        return self.product
