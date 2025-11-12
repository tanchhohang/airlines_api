from django.db import models
from django.contrib.auth.models import AbstractUser

#Abstract user provides authentication but need to define all the fields
class User(AbstractUser):
    userID = models.CharField(unique=True, max_length=100)
    api_pasword = models.CharField(max_length=100)
    agencyID = models.CharField(max_length=100)

class Sector(models.Model):
    sectorCode = models.CharField(unique=True, max_length=3)
    sectorName = models.CharField(max_length=100)

class Airline(models.Model):
    airlineID = models.CharField(max_length=50)
    airlineName = models.CharField(max_length=100)

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
    pax_type = models.CharField(max_length=10)
    title = models.CharField(max_length=10)
    gender = models.CharField(max_length=1)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nationality = models.CharField(max_length=2)
    ticket_no = models.CharField(max_length=50, blank=True, null=True)
    fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_surcharge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
