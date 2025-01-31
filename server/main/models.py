from django.db import models
import uuid
from django.conf import settings
from django.db.models import Q
from django.core.validators import RegexValidator

# Create your models here.
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return str(self.user)
    
    def getTransactions(self):
        transactions = Transaction.objects.filter(Q(sendingID=self) | Q(receivingID=self)).order_by('-date')
        return transactions

class Transaction(models.Model):
    transactionID = models.UUIDField(default=uuid.uuid4, primary_key=True)
    sendingID = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='sendingID')
    receivingID = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='receivingID')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=1,
        choices=[
            ('I', 'Incomplete'),
            ('C', 'Completed'),
            ('R', 'Reverted')
        ],
        default='I',
    )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.transactionID)

class AdminUser(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='adminuser')
    company_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return str(self.company_name)
    
    def getBuses(self):
        buses = Bus.objects.filter(company=self)
        return buses

class Seat(models.Model):
    type = models.CharField(max_length=10)

    def __str__(self):
        return str(self.type)

class Stop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=500)

    def __str__(self):
        return str(self.name)

class Bus(models.Model):
    license_plate = models.CharField(
        max_length=10, unique=True,
        validators = [
            RegexValidator(
                regex='^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$',
                message='License plate should be in the format XX00XX0000'
            )
        ]        
    )
    company = models.ForeignKey(AdminUser, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat, through='Bus_Seat')

    def getSeats(self):
        seats = Bus_Seat.objects.filter(bus=self)
        return seats
    
    def __str__(self):
        return str(self.license_plate)
    

class Bus_Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_seats = models.PositiveBigIntegerField()
    booked_seats = models.PositiveIntegerField(default=0)

    def avaiableSeats(self):
        return self.max_seats - self.booked_seats
    
    def __str__(self):
        return str(self.seat)

    class Meta:
        unique_together = ['bus', 'seat']
        constraints = [
            models.CheckConstraint(check=models.Q(max_seats__gte=models.F('booked_seats')), name='max_gte_booked')
        ]

class Route(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    route_number = models.PositiveIntegerField()
    stops = models.ManyToManyField(Stop, through='Route_Stops')
    start = models.DateTimeField()
    end = models.DateTimeField()
    stop_count = models.PositiveIntegerField()

    def getStops(self):
        stops = Route_Stops.objects.filter(route=self).order_by('order')
        return stops


class Route_Stops(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField()

    class Meta:
        unique_together = ['route', 'order', 'stop']
        constraints = [
            models.CheckConstraint(check=models.Q(arrival_time__lte=models.F('departure_time')), name='arrival_lt_departure')
        ]

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    start_stop = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='start_stop')
    end_stop = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='end_stop')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

class Ticket(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField()
    email = models.EmailField()
    gender = models.CharField(
        max_length=1,
        choices=[
            ('M', 'Male'),
            ('F', 'Female'),
            ('O', 'Other')
        ])
    