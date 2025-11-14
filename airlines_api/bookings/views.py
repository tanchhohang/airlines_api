from django.shortcuts import render
from .serializer import *
from rest_framework import viewsets, filters
from rest_framework.permissions import(
    IsAuthenticated,
    AllowAny
)
from .models import *
from .serializer import *

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class SectorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset= Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [IsAuthenticated]

class AirlinesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer
    permission_classes = [IsAuthenticated]

class PassengerViewSet(viewsets.ModelViewSet):
    queryset = Passenger.objects.all()
    serializer_class = PassengerSerializer
    permission_classes = [IsAuthenticated]

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSeriazlizer
    permission_classes = [IsAuthenticated]

