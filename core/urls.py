from django.urls import path
from .views import home, stations, my_bookings, book_station, payment_page, cancel_booking, login_view, logout_view, register_view,admin_dashboard, owner_dashboard

urlpatterns = [
    path('', home, name='home'),
    path('stations/', stations, name='stations'),
    path('my-bookings/', my_bookings, name='my_bookings'),
    path('book/<int:station_id>/', book_station, name='book_station'),
    path('payment/<int:station_id>/', payment_page, name='payment_page'),
    path('cancel-booking/<int:booking_id>/', cancel_booking, name='cancel_booking'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('owner-dashboard/', owner_dashboard, name='owner_dashboard'),
]