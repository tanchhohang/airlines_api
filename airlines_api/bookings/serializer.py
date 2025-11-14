from rest_framework import serializers
from .models import *

class UserSerializer(serializers.Serializer):
    class Meta:
        model = User
        fields = [
            'user_id',
            'api_password',
            'agency_id'
        ]

class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        feilds = '__all__'

class AirlineSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Airline
        fields = '__all__'

class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = '__all__'

class BookingSeriazlizer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'

