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
    passengers = PassengerSerializer(many=True, read_only=True)
    class Meta:
        model = Booking
        fields = ['pnr', 'airline', 'flight_id', 'flight_no', 'flight_date', 
                  'departure', 'arrival', 'contact_name', 'contact_email', 
                  'contact_mobile', 'reservation_status', 'ttl_date', 'ttl_time', 
                  'passengers']

class FlightAvailabilitySerializer(serializers.Serializer):
    sector_from = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.all())
    sector_to = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.all())
    flight_date = serializers.CharField()
    trip_type = serializers.CharField()
    return_date = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField(max_length=3)
    adult = serializers.IntegerField()
    child = serializers.IntegerField()
    client_ip = serializers.CharField(required = True)

class ReservationSerializer(serializers.Serializer):
    flight_id = serializers.CharField()
    return_flight_id = serializers.CharField(required = False, allow_blank = True)

class IssueTicketSerializer(serializers.Serializer):
    flight_id = serializers.CharField()
    return_flight_id = serializers.CharField(required = False, allow_blank = True)
    contact_name = serializers.CharField()
    contact_email = serializers.EmailField()
    contact_mobile = serializers.CharField()
    passenger_detail = PassengerSerializer(many=True)

class GetItinerarySerializer(serializers.Serializer):
    pno_no = serializers.CharField()
    ticket_no = serializers.CharField()
    airline_id = serializers.CharField()

class GetFlightDetailsSerializer(serializers.Serializer):
    flight_id = serializers.CharField()

class SalesReportSerializer(serializers.Serializer):
    from_date = serializers.CharField()
    to_date = serializers.CharField()

class GetPnrDetailSerializer(serializers.Serializer):
    pnr = serializers.CharField()
    last_name = serializers.CharField()
    