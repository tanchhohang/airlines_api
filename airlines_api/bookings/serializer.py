from rest_framework import serializers
from .models import Sector, Airline

class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        feilds = '__all__'

class AirlineSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Airline
        fields = '__all__'