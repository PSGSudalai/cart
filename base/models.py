from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Products(models.Model):
    item = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    # Add other fields as necessary

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
class updateCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created=models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    order_id = models.CharField(max_length=100, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    items = models.ManyToManyField(Cart)

    def __str__(self):
        return self.order_id





















