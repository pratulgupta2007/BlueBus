from django.shortcuts import render, redirect
from .models import (
    Wallet,
    Booking,
    Bus,
    Route,
    Route_Stops,
    Transaction,
    Ticket,
    OtpToken,
    Route_Seat
)


import uuid

import datetime
from django.contrib import messages

from decimal import Decimal
from django.db.models import Q
from django.db import transaction

from django.http import HttpResponseRedirect
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError

from django.core.mail import send_mail
from django.conf import settings

from .decorators import user_passes_test_with_logout

from collections import defaultdict

from django.utils import timezone

def getDuration(departure_time, arrival_time):
    duration = arrival_time - departure_time
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}hr {minutes}min"

# Create your views here.
def index(request):
    return render(request, "index.html")

def bookView(request):
    return render(request, "main/book.html")

def searchView(request):
    if request.method == "GET":
        from_location = request.GET.get("from")
        to_location = request.GET.get("to")
        travel_date = request.GET.get("date")

        if timezone.make_aware(datetime.datetime.strptime(travel_date, '%Y-%m-%d')).date() < timezone.now().date():
            messages.error(request, "Invalid Date")
            return render(request, "main/book.html")
        elif from_location == to_location:
            messages.error(request, "Invalid Locations")
            return render(request, "main/book.html")

        travel_day = str(timezone.make_aware(datetime.datetime.strptime(travel_date, '%Y-%m-%d')).isoweekday())

        if timezone.make_aware(datetime.datetime.strptime(travel_date, '%Y-%m-%d')).date() == timezone.now().date():
            routes_leaving = Route_Stops.objects.filter(
                Q(stop__name=from_location) & Q(arrival_day=travel_day) & Q(departure_time__gte=timezone.now().time())
            )
        else:
            routes_leaving = Route_Stops.objects.filter(Q(stop__name=from_location) & Q(arrival_day=travel_day))
        
        routes_reaching = Route_Stops.objects.filter(Q(stop__name=to_location))
        
        buses = []

        for route_leaving in routes_leaving:
            for route_reaching in routes_reaching:
                if (route_leaving.route == route_reaching.route) and (route_leaving.order < route_reaching.order) and (route_leaving.route.verified() == True):
                    
                    route = route_leaving.route
                    departure_time = datetime.datetime.combine(timezone.now().date(), route_leaving.departure_time)
                    arrival_time = datetime.datetime.combine(timezone.now().date(), route_reaching.arrival_time)
                    duration_str = getDuration(departure_time, arrival_time)

                    departure_time_12hr = route_leaving.departure_time.strftime("%I:%M %p")
                    arrival_time_12hr = route_reaching.arrival_time.strftime("%I:%M %p")

                    day_offset = int(route_reaching.arrival_day) - int(travel_day)
                    arrival_day = timezone.make_aware(datetime.datetime.strptime(travel_date, '%Y-%m-%d')).date() + datetime.timedelta(days=day_offset)
                    arrival_day = arrival_day.strftime("%b %d")


                    buses.append([route, departure_time_12hr, arrival_time_12hr, 
                                  duration_str, arrival_day,
                                  route.getStartingPrice(), route.getAvailableSeats(timezone.make_aware(datetime.datetime.strptime(travel_date, '%Y-%m-%d')), 
                                                                                    start = route_leaving, end = route_reaching)])    

        context = {
            "buses": buses,
            "from_location": from_location,
            "to_location": to_location,
            "travel_date": travel_date
        }
        return render(request, "main/search.html", context=context)
    return render(request, "main/search.html")


@user_passes_test_with_logout()
def bookingView(request, route_id, start_stop, end_stop, date):
    
    if request.method == "POST":
        with transaction.atomic():
            try:
                route = Route.objects.get(id=route_id)
            except Route.DoesNotExist:
                messages.error(request, "Invalid Route")
                return render(request, "blank.html")

            try:
                start = Route_Stops.objects.get(Q(stop__name=start_stop) & Q(route=route))
                end = Route_Stops.objects.get(Q(stop__name=end_stop) & Q(route=route))
            except Route_Stops.DoesNotExist:
                messages.error(request, "Invalid Stops")
                return render(request, "blank.html")

            if datetime.datetime.strptime(date, '%Y-%m-%d').date() < timezone.now().date():
                messages.error(request, "Invalid Date")
                return render(request, "blank.html")
            elif start == end:
                messages.error(request, "Invalid Locations")
                return render(request, "blank.html")

            travel_day = str(timezone.make_aware(datetime.datetime.strptime(date, '%Y-%m-%d')).isoweekday())

            if int(start.arrival_day) != int(travel_day):
                messages.error(request, "Invalid Day")
                return render(request, "blank.html")

            seats_booked = {}
            price = 0
            for seat in route.getSeats():
                try:
                    count = int(request.POST.get(str(seat.id)))
                    seats_booked[seat.seat.seat.type] = (seat.price, count)
                    price += seat.price * count
                except ValueError:
                    pass
            
            if seats_booked == {}:
                messages.error(request, "No Seats Selected")
                return redirect("booking", route_id=route_id, start_stop=start_stop, end_stop=end_stop, date=date)

            user = request.user
            try:
                wallet = Wallet.objects.filter(user=(request.user)).first()
            except Wallet.DoesNotExist:
                wallet = Wallet.objects.create(user=(request.user))

            admin_user = route.bus.company.user
            admin_wallet = Wallet.objects.filter(user=admin_user).first()

            if wallet.balance < price:
                messages.error(request, "Insufficient Balance")
                return redirect("balance")
            
            booking = Booking.objects.create(
                user = user,
                bus = route.bus,
                start_stop = start,
                end_stop = end,
                total_price = price,
                date = timezone.make_aware(datetime.datetime.strptime(date, '%Y-%m-%d'))
            )

            for type in seats_booked.keys():
                price, count = seats_booked[type]
                for i in range(count):
                    Ticket.objects.create(
                        booking = booking,
                        seat_type = type,
                    )
                
            context = {
                "booking": booking,
                "seats_booked": seats_booked
            }

            return render(request, "account/billing.html", context=context)

    try:
        route = Route.objects.get(id=route_id)
    except Route.DoesNotExist:
        messages.error(request, "Invalid Route")
        return render(request, "blank.html")

    try:
        start = Route_Stops.objects.get(Q(stop__name=start_stop) & Q(route=route))
        end = Route_Stops.objects.get(Q(stop__name=end_stop) & Q(route=route))
    except Route_Stops.DoesNotExist:
        messages.error(request, "Invalid Stops")
        return render(request, "blank.html")
    
    if timezone.make_aware(datetime.datetime.strptime(date, '%Y-%m-%d')).date() < timezone.now().date():
            messages.error(request, "Invalid Date")
            return render(request, "blank.html")
    elif start == end:
        messages.error(request, "Invalid Locations")
        return render(request, "blank.html")

    travel_day = str(timezone.make_aware(datetime.datetime.strptime(date, '%Y-%m-%d')).isoweekday())

    if int(start.arrival_day) != int(travel_day):
        messages.error(request, "Invalid Day")
        return render(request, "blank.html")

    context = {
        "route": route,
        "start": start,
        "end": end,
        "seats": [(seat, seat.getAvailableSeats(timezone.make_aware(datetime.datetime.strptime(date, '%Y-%m-%d')), start = start, end = end)) 
                  for seat in route.getSeats()],
    }
    return render(request, "main/booking.html", context=context)

def verificationView(request, booking_id):
    
    with transaction.atomic():
        try:
            booking = Booking.objects.get(temp_id=booking_id)
        except Booking.DoesNotExist:
            messages.error(request, "Invalid Booking")
            return render(request, "blank.html")
        
        if booking.user != request.user:
            messages.error(request, "Access Denied")
            return render(request, "blank.html")
        
        if booking.transaction is not None:
            messages.error(request, "Booking Already Verified")
            return redirect("bookinglist")
        
        if request.method == "POST":
            otp = request.POST.get("otp_code")
            otp_token = OtpToken.objects.filter(booking=booking).first()
            if otp_token.otp == otp and otp_token.is_valid():
                
                try:
                    wallet = Wallet.objects.filter(user=(request.user)).first()
                    wallet.balance -= booking.total_price
                    wallet.save()
                except IntegrityError:
                    booking.delete()
                    messages.error(request, "Insufficient Balance")
                    return redirect("balance")
                
                ticketlist = Ticket.objects.filter(booking=booking)

                try:
                    for ticket in ticketlist:
                        routeseat = Route_Seat.objects.filter(route=booking.start_stop.route).filter(seat__seat__type=ticket.seat_type).first()
                        if routeseat.getAvailableSeats(booking.date, start = booking.start_stop, end = booking.end_stop) <= 0:
                            raise IntegrityError
                except IntegrityError or ValidationError:
                    booking.delete()
                    messages.error(request, "Seats Unavailable")
                    return redirect("booking", route_id=booking.start_stop.route.id, start_stop=booking.start_stop.stop.name, 
                                    end_stop=booking.end_stop.stop.name, date=booking.date)

                admin_user = booking.bus.company.user
                admin_wallet = Wallet.objects.filter(user=admin_user).first()
                admin_wallet.balance += booking.total_price
                admin_wallet.save()

                booking_transaction = Transaction.objects.create(
                    sendingID = wallet,
                    receivingID = admin_wallet,
                    amount = booking.total_price,
                    status = "C",
                )

                booking.transaction = booking_transaction
                booking.verified = True
                booking.save()

                messages.success(request, "Booking Successful")
                return redirect("passengerinfo", booking_id=booking_id)
            else:
                messages.error(request, "Invalid OTP")
                return render(request, "main/verification.html", context={"booking":booking})

        try:
            otp = OtpToken.objects.get(booking=booking, user=request.user)
            otp.delete()
        except OtpToken.DoesNotExist:
           pass

        otp = OtpToken.objects.create(booking=booking, user=request.user, otp=OtpToken.generateOTP())

        subject = "Email Verification"
        message = f"""
                Hi {request.user.username}, here is your OTP {otp.otp}
                """
        sender = settings.EMAIL_HOST_USER
        receiver = [request.user.email,]
        send_mail(
            subject,
            message,
            sender,
            receiver,
            fail_silently=False,
        )
        
        context = {
            "booking":booking
        }

        return render(request, "main/verification.html", context = context)

def passengerInfo(request, booking_id):
    
    try:
        booking = Booking.objects.get(temp_id=booking_id)
    except:
        messages.error(request, "Invalid Booking")
        return render(request, "blank.html")

    if booking.user != request.user or not booking.verified:
        messages.error(request, "Access Denied")
        return render(request, "blank.html")
    
    ticketlist = Ticket.objects.filter(booking=booking)

    if request.method == "POST":
        for ticket in ticketlist:
            name = request.POST.get(f"name_{ticket.id}")
            age = request.POST.get(f"age_{ticket.id}")
            email = request.POST.get(f"email_{ticket.id}")
            gender = request.POST.get(f"gender_{ticket.id}")

            ticket.name = name
            ticket.age = age
            ticket.email = email
            ticket.gender = gender
            ticket.save()
        
        messages.success(request, "Passenger Information Updated")
        return redirect("bookinglist")

    tickets = {}
    for ticket in ticketlist:
        if ticket.seat_type not in tickets:
            tickets[ticket.seat_type] = []
        tickets[ticket.seat_type].append(ticket)

    return  render(request, "main/passengerinfo.html", context={"tickets":tickets})

def refundView(request, booking_id):

    try:
        booking = Booking.objects.get(temp_id=booking_id)
    except Booking.DoesNotExist:
        messages.error(request, "Invalid Booking")
        return render(request, "blank.html")

    if booking.user != request.user or not booking.verified:
        messages.error(request, "Access Denied")
        return render(request, "blank.html")

    if request.method == "POST":
        with transaction.atomic():
            try:
                booking.revertTicket()
            except ValidationError:
                messages.error(request, "Refund Failed")
                return redirect("bookinglist")

            messages.success(request, "Refund Successful")
            return redirect("bookinglist")

    return render(request, "main/refund.html", context={"booking":booking})


def profileView(request):
    try:
        Wallet.objects.get(user=(request.user))
    except Wallet.DoesNotExist:
        Wallet.objects.create(user=(request.user))
    context = {
        "balance": Wallet.objects.filter(user=(request.user)).first().balance
    }
    return render(request, "account/profile.html", context=context)

def addBalanceView(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        wallet = Wallet.objects.filter(user=(request.user)).first()
        wallet.balance += Decimal(amount)
        wallet.save()

        next = request.POST.get('next', '/')
        return HttpResponseRedirect(next)
    
    try:
        Wallet.objects.get(user=(request.user))
    except Wallet.DoesNotExist:
        Wallet.objects.create(user=(request.user))
    
    context = {
        "balance": Wallet.objects.filter(user=(request.user)).first().balance
    }
    return render(request, "account/balance.html", context=context)

def bookingList(request):
    bookings = Booking.objects.filter(user=(request.user)).filter(verified=True)
    context = {"bookings": bookings}
    return render(request, "account/bookings.html", context=context)

def transactionsView(request):
    transactions = Wallet.objects.filter(user=(request.user)).first().getTransactions()
    context = {"transactions": transactions}
    return render(request, "account/transactions.html", context=context)