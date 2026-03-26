from django.db import models
from django.contrib.auth.models import User
from stations.models import Station


class Booking(models.Model):
    STATUS_CHOICES = [
        ('Booked', 'Booked'),
        ('Verified', 'Verified'),
        ('Charging', 'Charging'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    TIME_SLOT_CHOICES = [
        ('09:00 AM - 10:00 AM', '09:00 AM - 10:00 AM'),
        ('10:00 AM - 11:00 AM', '10:00 AM - 11:00 AM'),
        ('11:00 AM - 12:00 PM', '11:00 AM - 12:00 PM'),
        ('12:00 PM - 01:00 PM', '12:00 PM - 01:00 PM'),
        ('02:00 PM - 03:00 PM', '02:00 PM - 03:00 PM'),
        ('03:00 PM - 04:00 PM', '03:00 PM - 04:00 PM'),
        ('04:00 PM - 05:00 PM', '04:00 PM - 05:00 PM'),
        ('05:00 PM - 06:00 PM', '05:00 PM - 06:00 PM'),
    ]

    VEHICLE_TYPE_CHOICES = [
        ('2 Wheeler', '2 Wheeler'),
        ('4 Wheeler', '4 Wheeler'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Prepaid', 'Prepaid'),
        ('Postpaid', 'Postpaid'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)

    booking_id = models.CharField(max_length=30, unique=True, blank=True, null=True)

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='4 Wheeler')
    vehicle_number = models.CharField(max_length=30, blank=True, null=True)

    booking_date = models.DateField(default='2026-01-01')
    time_slot = models.CharField(max_length=30, choices=TIME_SLOT_CHOICES, default='09:00 AM - 10:00 AM')

    booking_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Booked')

    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Prepaid'
    )

    verified_at = models.DateTimeField(blank=True, null=True)
    charging_started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} - {self.station.name} - {self.status}"