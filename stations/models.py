from django.db import models


class Station(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    address = models.TextField()
    charger_type = models.CharField(max_length=100)
    total_slots = models.PositiveIntegerField()
    available_slots = models.PositiveIntegerField()
    price_per_kwh = models.DecimalField(max_digits=6, decimal_places=2)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.000000)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.000000)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name