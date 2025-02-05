from django.db import models
import uuid
from django.conf import settings
from django.db.models import Q
from django.core.validators import RegexValidator

from django.utils import timezone
import datetime

from django.core.exceptions import ValidationError

# Create your models here.
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return str(self.user)
    
    def getTransactions(self):
        transactions = Transaction.objects.filter(Q(sendingID=self) | Q(receivingID=self)).order_by('-date')
        return transactions

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(balance__gte=0), name='balance_non_negative')
        ]

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

    class Meta:
        verbose_name = 'Bus'
        verbose_name_plural = 'Buses'
    

class Bus_Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    max_seats = models.PositiveIntegerField()
    
    def __str__(self):
        return str(self.seat)

    class Meta:
        unique_together = ['bus', 'seat']
        verbose_name = 'Bus Seat'
        verbose_name_plural = 'Bus Seats'

    def clean(self):
        super().clean()
        if self.max_seats == 0:
            raise ValidationError('Max seats cannot be 0')

class Route_Seat(models.Model):
    route = models.ForeignKey('Route', on_delete=models.CASCADE)
    seat = models.ForeignKey(Bus_Seat, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['route', 'seat']
        verbose_name = 'Seat pricing for route'
        verbose_name_plural = 'Seat pricing for routes'

    def __str__(self):
        return str(self.route.route_number) + ' - ' + str(self.seat.seat.type)
    
    def getAvailableSeats(self, date):
        return self.seat.max_seats - self.booked_seats(date)
    
    def booked_seats(self, date):
        tickets = Ticket.objects.filter(Q(seat_type=self.seat.seat.type) & Q(booking__start_stop__route=self.route) & Q(booking__date = date)).count()
        return tickets
    
    def clean(self):
        super().clean()
        if self.price <= 0:
            raise ValidationError('Price should be greater than or equal to 0')
    
    def save(self, date, *args, **kwargs):
        if self.price <= 0:
            raise ValidationError('Price should be greater than or equal to 0')
        if self.booked_seats(date) > self.seat.max_seats:
            raise ValidationError('Booked seats should be less than or equal to max seats')
        super().save(*args, **kwargs)



class Route(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    route_number = models.PositiveIntegerField()
    stops = models.ManyToManyField(Stop, through='Route_Stops')
    stop_count = models.PositiveIntegerField()
    seats = models.ManyToManyField(Bus_Seat, through='Route_Seat')
    active = models.BooleanField(default=True)

    def verified(self):
        return Route_Stops.objects.filter(route=self).count() == self.stop_count and self.stop_count > 1 and self.seats.count() > 0 and self.active

    def getStops(self):
        stops = Route_Stops.objects.filter(route=self).order_by('order')
        return stops
    
    def getSeats(self):
        seats = Route_Seat.objects.filter(route=self).order_by('price')
        return seats
    
    def getStartingPrice(self):
        prices = Route_Seat.objects.filter(route=self)
        return prices.aggregate(models.Min('price'))['price__min']
    
    def getAvailableSeats(self, date):
        max = sum([seat.max_seats for seat in self.bus.getSeats()])
        booked = sum([seat.booked_seats(date) for seat in self.getSeats()])
        return max - booked

    
    def clean(self):
        super().clean()
        if self.stop_count < 2:
            raise ValidationError('Stop count should be greater than or equal to 2')

class Route_Stops(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    arrival_day = models.CharField(max_length=10, 
                                   choices=[
                                        ('1', 'Monday'),
                                        ('2', 'Tuesday'),
                                        ('3', 'Wednesday'),
                                        ('4', 'Thursday'),
                                        ('5', 'Friday'),
                                        ('6', 'Saturday'),
                                        ('7', 'Sunday')])
    departure_day = models.CharField(max_length=10, 
                                     choices=[
                                        ('1', 'Monday'),
                                        ('2', 'Tuesday'),
                                        ('3', 'Wednesday'),
                                        ('4', 'Thursday'),
                                        ('5', 'Friday'),
                                        ('6', 'Saturday'),
                                        ('7', 'Sunday')])
    arrival_time = models.TimeField()
    departure_time = models.TimeField()

    class Meta:
        unique_together = ['route', 'stop']
        verbose_name = 'Route Stop'
        verbose_name_plural = 'Route Stops'
    
    def __str__(self):
        return str(self.route.route_number) + ' - ' + str(self.stop.name)
    
    def clean(self):
        super().clean()
        try:
            if int(self.arrival_day) == int(self.departure_day):
                if self.arrival_time > self.departure_time:
                    raise ValidationError('Arrival time should be before departure time')
            elif int(self.arrival_day) > int(self.departure_day):
                raise ValidationError('Arrival day should be before departure day')
            if self.order > self.route.stop_count:
                raise ValidationError('Order should be less than or equal to stop count')
            if self.order != 1:
                try:
                    prev_stop = Route_Stops.objects.get(route__id=self.route.id, order=self.order-1)
                    if int(self.arrival_day) == int(prev_stop.departure_day):
                        if self.arrival_time < prev_stop.departure_time:
                            raise ValidationError('Previous stop departure time should be before arrival time')
                    elif int(self.arrival_day) < int(prev_stop.departure_day):
                        raise ValidationError('Previous stop departure day should be before arrival day')
                except Route_Stops.DoesNotExist:
                    raise ValidationError('Previous stop does not exist')
            
            if self.order != self.route.stop_count:
                try:
                    next_stop = Route_Stops.objects.get(route__id=self.route.id, order=self.order+1)
                    if int(self.departure_day) == int(next_stop.arrival_day):
                        if self.departure_time > next_stop.arrival_time:
                            raise ValidationError('Next stop arrival time should be after departure time')
                    elif int(self.departure_day) > int(next_stop.arrival_day):
                        raise ValidationError('Next stop arrival day should be after departure day')
                except Route_Stops.DoesNotExist:
                    pass
            
            if self.order == self.route.stop_count:
                upper_stop = self
                lower_stop = Route_Stops.objects.get(route=self.route, order=1)
                for route in Route.objects.filter(Q(bus=self.route.bus)):
                    if route.verified() and route != self.route:
                        upper = Route_Stops.objects.get(route=route, order=route.stop_count)
                        lower = Route_Stops.objects.get(route=route, order=1)

                        if int(upper.arrival_day) in range (int(lower_stop.departure_day), int(upper_stop.arrival_day)+1):
                            if int(upper.arrival_day) == int(lower_stop.departure_day):
                                if upper.arrival_time > lower_stop.departure_time:
                                    raise ValidationError('Route overlapping')
                            elif int(upper.arrival_day) == int(upper_stop.arrival_day):
                                if upper.arrival_time <= upper_stop.arrival_time:
                                    raise ValidationError('Route overlapping')
                            else:
                                raise ValidationError('Route overlapping')
                        
                        if int(lower.departure_day) in range (int(lower_stop.departure_day), int(upper_stop.arrival_day)+1):
                            if int(lower.departure_day) == int(lower_stop.departure_day):
                                if lower.departure_time >= lower_stop.departure_time:
                                    raise ValidationError('Route overlapping')
                            elif int(lower.departure_day) == int(upper_stop.arrival_day):
                                if lower.departure_time < upper_stop.arrival_time:
                                    raise ValidationError('Route overlapping')
                            else:
                                raise ValidationError('Route overlapping')
        except ValueError:
            raise ValidationError('Invalid day format')

class Booking(models.Model):
    temp_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    date = models.DateTimeField()
    start_stop = models.ForeignKey(Route_Stops, on_delete=models.CASCADE, related_name='start_stop')
    end_stop = models.ForeignKey(Route_Stops, on_delete=models.CASCADE, related_name='end_stop')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    verified = models.BooleanField(default=False)

    def getDate(self):
        return self.date.date()

class Ticket(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=True)
    seat_type = models.CharField(max_length=10)
    age = models.PositiveSmallIntegerField(null=True)
    email = models.EmailField(null=True)
    gender = models.CharField(
        max_length=1,
        choices=[
            ('M', 'Male'),
            ('F', 'Female'),
            ('O', 'Other')
        ],
        null=True)

class OtpToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='otp_token')
    otp = models.CharField(max_length=6)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return str(self.otp)

    def is_valid(self):
        return (timezone.now() - self.created) < datetime.timedelta(minutes=5)
    
    @staticmethod
    def generateOTP():
        import random
        otp = str(random.randint(100000, 999999))
        return otp
    