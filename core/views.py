from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from stations.models import Station, StationOwner
from bookings.models import Booking
from django.core.mail import send_mail
from django.conf import settings
import re
from django.contrib.auth.decorators import user_passes_test
from datetime import datetime, date
import qrcode
import base64
from io import BytesIO


def auto_cancel_expired_bookings():
    now = datetime.now()

    slot_end_times = {
        "09:00 AM - 10:00 AM": "10:00",
        "10:00 AM - 11:00 AM": "11:00",
        "11:00 AM - 12:00 PM": "12:00",
        "12:00 PM - 01:00 PM": "13:00",
        "02:00 PM - 03:00 PM": "15:00",
        "03:00 PM - 04:00 PM": "16:00",
        "04:00 PM - 05:00 PM": "17:00",
        "05:00 PM - 06:00 PM": "18:00",
    }

    active_bookings = Booking.objects.filter(status="Booked")

    for booking in active_bookings:
        slot_end = slot_end_times.get(booking.time_slot)

        if slot_end:
            booking_end_datetime = datetime.strptime(
                f"{booking.booking_date} {slot_end}", "%Y-%m-%d %H:%M"
            )

            grace_end_time = booking_end_datetime.replace(
                minute=booking_end_datetime.minute + 15
            )

            if now > grace_end_time:
                booking.status = "Cancelled"
                booking.save()

                booking.station.available_slots += 1
                booking.station.save()


def is_station_owner(user):
    return StationOwner.objects.filter(user=user).exists()


def home(request):
    return render(request, "home.html")


def stations(request):
    all_stations = Station.objects.all()

    search_city = request.GET.get("city", "").strip()
    selected_charger_type = request.GET.get("charger_type", "").strip()

    if search_city:
        all_stations = all_stations.filter(city__icontains=search_city)

    all_stations = list(all_stations)

    charger_type_set = set()
    for station in Station.objects.all():
        charger_types = [
            item.strip() for item in station.charger_type.split(",") if item.strip()
        ]
        for ctype in charger_types:
            charger_type_set.add(ctype)

    charger_types = sorted(charger_type_set)

    if selected_charger_type:
        filtered_stations = []
        for station in all_stations:
            station_charger_types = [
                item.strip().lower()
                for item in station.charger_type.split(",")
                if item.strip()
            ]
            if selected_charger_type.lower() in station_charger_types:
                filtered_stations.append(station)
        all_stations = filtered_stations

    for station in all_stations:
        station.charger_type_list = [
            item.strip() for item in station.charger_type.split(",") if item.strip()
        ]

    context = {
        "stations": all_stations,
        "search_city": search_city,
        "selected_charger_type": selected_charger_type,
        "charger_types": charger_types,
    }

    return render(request, "stations.html", context)


def my_bookings(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login to view your bookings.")
        return redirect("login")

    auto_cancel_expired_bookings()

    user_bookings = Booking.objects.filter(user=request.user).order_by("-booking_time")

    for booking in user_bookings:
        if booking.booking_id:
            qr = qrcode.make(booking.booking_id)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            qr_image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            booking.qr_code_base64 = qr_image_base64
        else:
            booking.qr_code_base64 = None

    return render(request, "my_bookings.html", {"bookings": user_bookings})


def book_station(request, station_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please login to book a slot.")
        return redirect("login")

    station = get_object_or_404(Station, id=station_id)

    if station.available_slots <= 0:
        messages.error(request, "No slots available.")
        return redirect("stations")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        address = request.POST.get("address", "").strip()
        vehicle_type = request.POST.get("vehicle_type")
        vehicle_number = request.POST.get("vehicle_number", "").strip()
        booking_date = request.POST.get("booking_date")
        time_slot = request.POST.get("time_slot")

        existing_booking = Booking.objects.filter(
            station=station,
            booking_date=booking_date,
            time_slot=time_slot,
            status="Booked",
        ).exists()

        if existing_booking:
            messages.error(
                request, "This time slot is already booked. Please select another slot."
            )
            return render(request, "booking_form.html", {"station": station})

        if not booking_date:
            messages.error(request, "Please select a charging date.")
            return render(request, "booking_form.html", {"station": station})

        if not time_slot:
            messages.error(request, "Please select a time slot.")
            return render(request, "booking_form.html", {"station": station})

        if booking_date < str(date.today()):
            messages.error(request, "You cannot book a past date.")
            return render(request, "booking_form.html", {"station": station})

        if not re.fullmatch(r"[A-Za-z ]+", full_name):
            messages.error(request, "Full name should contain only letters and spaces.")
            return render(request, "booking_form.html", {"station": station})

        if not re.fullmatch(r"[0-9]{10}", phone_number):
            messages.error(request, "Phone number must contain exactly 10 digits.")
            return render(request, "booking_form.html", {"station": station})

        if not vehicle_type:
            messages.error(request, "Please select vehicle type.")
            return render(request, "booking_form.html", {"station": station})

        if vehicle_number and not re.fullmatch(r"[A-Za-z0-9 ]+", vehicle_number):
            messages.error(
                request, "Vehicle number can contain only letters, numbers, and spaces."
            )
            return render(request, "booking_form.html", {"station": station})

        request.session["pending_booking"] = {
            "station_id": station.id,
            "full_name": full_name,
            "email": email,
            "phone_number": phone_number,
            "address": address,
            "vehicle_type": vehicle_type,
            "vehicle_number": vehicle_number,
            "booking_date": booking_date,
            "time_slot": time_slot,
        }

        return redirect("payment_page", station_id=station.id)

    return render(request, "booking_form.html", {"station": station})


def cancel_booking(request, booking_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect("login")

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status in ["Booked", "Verified"]:
        booking.status = "Cancelled"
        booking.save()

        booking.station.available_slots += 1
        booking.station.save()

        messages.success(request, "Booking cancelled successfully.")
    else:
        messages.error(request, "This booking is already cancelled.")

    return redirect("my_bookings")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("home")


def register_view(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not re.fullmatch(r"[A-Za-z ]+", full_name):
            messages.error(request, "Full name should contain only letters and spaces.")
            return redirect("register")

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Please enter a valid email address.")
            return redirect("register")

        if not re.fullmatch(r"[A-Za-z0-9_]+", username):
            messages.error(
                request, "Username can contain only letters, numbers, and underscore."
            )
            return redirect("register")

        if len(username) < 4:
            messages.error(request, "Username must be at least 4 characters long.")
            return redirect("register")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")

        user = User.objects.create_user(
            username=username, email=email, password=password, first_name=full_name
        )
        user.save()

        messages.success(request, "Registration successful. Please login.")
        return redirect("login")

    return render(request, "register.html")


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    auto_cancel_expired_bookings()

    total_users = User.objects.count()
    total_stations = Station.objects.count()
    total_bookings = Booking.objects.count()
    active_bookings = Booking.objects.filter(status="Booked").count()
    cancelled_bookings = Booking.objects.filter(status="Cancelled").count()
    recent_bookings = Booking.objects.select_related("station", "user").order_by(
        "-booking_time"
    )[:5]

    context = {
        "total_users": total_users,
        "total_stations": total_stations,
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "cancelled_bookings": cancelled_bookings,
        "recent_bookings": recent_bookings,
    }

    return render(request, "admin_dashboard.html", context)


@user_passes_test(is_station_owner, login_url="login")
def owner_dashboard(request):
    auto_cancel_expired_bookings()

    station_owner = StationOwner.objects.get(user=request.user)
    owner_station = station_owner.station

    if request.method == "POST":
        action = request.POST.get("action")
        booking_id_input = request.POST.get("booking_id")

        try:
            booking = Booking.objects.get(
                booking_id=booking_id_input, station=owner_station
            )

            if action in ["verify", "scan_qr"]:
                if booking.status == "Booked":
                    booking.status = "Verified"
                    booking.verified_at = datetime.now()
                    booking.save()

                    if action == "scan_qr":
                        messages.success(
                            request, "QR scanned successfully ✅ User verified."
                        )
                    else:
                        messages.success(request, "User verified successfully ✅")
                else:
                    messages.error(request, f"Booking is already {booking.status}")

            elif action == "start_charging":
                if booking.status == "Verified":
                    booking.status = "Charging"
                    booking.charging_started_at = datetime.now()
                    booking.save()
                    messages.success(request, "Charging started successfully ⚡")
                else:
                    messages.error(
                        request, "Only verified bookings can start charging."
                    )

            elif action == "complete_charging":
                if booking.status == "Charging":
                    booking.status = "Completed"
                    booking.completed_at = datetime.now()
                    booking.save()

                    booking.station.available_slots += 1
                    booking.station.save()

                    messages.success(
                        request,
                        "Charging completed successfully ✅ Slot is now available.",
                    )
                else:
                    messages.error(request, "Only charging bookings can be completed.")

        except Booking.DoesNotExist:
            messages.error(request, "Invalid Booking ID ❌")

    station_bookings = Booking.objects.filter(station=owner_station).order_by(
        "-booking_date", "-booking_time"
    )

    return render(
        request,
        "owner_dashboard.html",
        {
            "owner_station": owner_station,
            "station_bookings": station_bookings,
        },
    )


def payment_page(request, station_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect("login")

    station = get_object_or_404(Station, id=station_id)
    pending_booking = request.session.get("pending_booking")

    if not pending_booking or pending_booking.get("station_id") != station.id:
        messages.error(
            request, "No pending booking found. Please fill the booking form again."
        )
        return redirect("book_station", station_id=station.id)

    amount = float(station.price_per_kwh) * 10

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")

        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return render(
                request,
                "payment.html",
                {
                    "station": station,
                    "pending_booking": pending_booking,
                    "amount": amount,
                },
            )

        existing_booking = Booking.objects.filter(
            station=station,
            booking_date=pending_booking["booking_date"],
            time_slot=pending_booking["time_slot"],
            status="Booked",
        ).exists()

        if existing_booking:
            messages.error(
                request, "This time slot is already booked. Please select another slot."
            )
            return redirect("book_station", station_id=station.id)

        # Decide payment status
        if payment_method == "Pay at Station":
            payment_status = "Postpaid"
        else:
            payment_status = "Prepaid"

        booking = Booking.objects.create(
            user=request.user,
            station=station,
            full_name=pending_booking["full_name"],
            email=pending_booking["email"],
            phone_number=pending_booking["phone_number"],
            address=pending_booking["address"],
            vehicle_type=pending_booking["vehicle_type"],
            vehicle_number=pending_booking["vehicle_number"],
            booking_date=pending_booking["booking_date"],
            time_slot=pending_booking["time_slot"],
            status="Booked",
            payment_method=payment_method,
            payment_status=payment_status,
        )

        booking.booking_id = f"CS{booking.id + 1000}"
        booking.save()

        station.available_slots -= 1
        station.save()

        subject = "ChargeSmart Booking Confirmation"

        if payment_method == "Pay at Station":
            payment_text = "Pay at Station (Cash / Postpaid)"
            amount_text = "To be paid at station"
        else:
            payment_text = payment_method
            amount_text = f"₹{amount}"

        message = (
            f"Hello {booking.full_name},\n\n"
            f"Your EV charging slot has been booked successfully.\n\n"
            f"Booking Details:\n"
            f"Booking ID: {booking.booking_id}\n"
            f"Station: {booking.station.name}\n"
            f"City: {booking.station.city}\n"
            f"Charger Type: {booking.station.charger_type}\n"
            f"Price: ₹{booking.station.price_per_kwh}/kWh\n"
            f"Booking Date: {booking.booking_date}\n"
            f"Time Slot: {booking.time_slot}\n"
            f"Vehicle Type: {booking.vehicle_type}\n"
            f"Booking Status: {booking.status}\n"
            f"Payment Method: {payment_text}\n"
            f"Payment Status: {booking.payment_status}\n"
            f"Amount: {amount_text}\n"
            f"Booked On: {booking.booking_time}\n"
            f"Phone Number: {booking.phone_number}\n"
            f"Address: {booking.address}\n"
            f'Vehicle Number: {booking.vehicle_number if booking.vehicle_number else "Not Provided"}\n\n'
            f"Thank you for using ChargeSmart."
        )

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [booking.email],
                fail_silently=False,
            )
        except Exception:
            pass

        if "pending_booking" in request.session:
            del request.session["pending_booking"]

        if payment_method == "Pay at Station":
            messages.success(
                request,
                "Booking confirmed successfully. Please pay at station during charging.",
            )
        else:
            messages.success(
                request,
                f"Payment successful via {payment_method}. Your EV slot is confirmed.",
            )

        return redirect("my_bookings")

    return render(
        request,
        "payment.html",
        {
            "station": station,
            "pending_booking": pending_booking,
            "amount": amount,
        },
    )
