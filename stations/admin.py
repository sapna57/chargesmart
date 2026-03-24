from django.contrib import admin
from .models import Station


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'city',
        'charger_type',
        'available_slots',
        'total_slots',
        'price_per_kwh',
        'latitude',
        'longitude',
    )
    search_fields = ('name', 'city', 'charger_type')
    list_filter = ('city', 'charger_type')