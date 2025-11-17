from django.db import models
from django.contrib.auth.models import AbstractUser

class PassengerType(models.TextChoices):
    ADULT = 'ADT', 'Adult'
    CHILD = 'CHD', 'Child'
    INFANT = 'INF', 'Infant'

#Abstract user provides authentication but need to define all the fields
class User(AbstractUser):
    user_id = models.CharField(unique=True, max_length=100)
    api_pasword = models.CharField(max_length=100)
    agency_id = models.CharField(max_length=100)

class Sector(models.Model):
    sector_code = models.CharField(unique=True, max_length=3)
    sector_name = models.CharField(max_length=100)

class Airline(models.Model):
    airline_id = models.CharField(max_length=50)
    airline_name = models.CharField(max_length=100)
    fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pnr = models.CharField(max_length=50)
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE)
    flight_id = models.CharField(max_length=100)
    flight_no = models.CharField(max_length=20)
    flight_date = models.DateField()
    departure = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='departures')
    arrival = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='arrivals')  
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_mobile = models.CharField(max_length=20)
    reservation_status = models.CharField(max_length=20)
    ttl_date = models.DateField(null=True, blank=True)
    ttl_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Passenger(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    pax_type = models.CharField(
        choices=PassengerType.choices,
        default=PassengerType.ADULT
    )
    title = models.CharField(max_length=10)
    gender = models.CharField(max_length=1)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nationality = models.CharField(max_length=2)
    ticket_no = models.CharField(max_length=50, blank=True, null=True)
    fuel_surcharge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
