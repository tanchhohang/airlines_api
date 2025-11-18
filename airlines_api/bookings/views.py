import requests
from django.shortcuts import render
from .serializer import *
from rest_framework import viewsets, filters
from rest_framework.permissions import(
    IsAuthenticated,
    AllowAny
)
from .models import *
from .serializer import *
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
import xml.etree.ElementTree as ET

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class SectorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset= Sector.objects.all()  
    serializer_class = SectorSerializer
    permission_classes = [AllowAny]

    @action(methods=['POST'],detail=False)
    def sector_code(self,request):
        user = request.user
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:SectorCode>
                    <strUserId>{user.user_id}</strUserId>
                </book:SectorCode>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        try:
            response = requests.post( #send SOAP request to server
                'SOAP_ENDPOINT_URL',
                data=soap_body,
                headers={'Content-Type': 'text/xml'}
            )
            root = ET.fromstring(response.text) #parse xml response to str
            sector_data = root.find(".//{http://booking.us.org/}return").text.strip()
            sector_xml = ET.fromstring(sector_data)
            sector_list = []

            for sector in sector_xml.findall('Sector'):
                code = sector.find('SectorCode').text
                name = sector.find('SectorName').text

                #save/update to database
                sector_obj, created = Sector.objects.update_or_create(
                    sector_code=code,
                    defaults={"sector_name": name}
                )

                sector_list.append(sector_obj)

            serializer = SectorSerializer(sector_list, many=True)
            return Response({
                'sectors': serializer.data
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AirlinesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=['POST'],detail=False)
    def check_balance(self,request):
        user = request.user
        airline_id = request.data.get('airline_id')
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:CheckBalance>
                    <strUserId>{user.user_id}</strUserId>
                    <strAirlineId>{airline_id}</strAirlineId>
                </book:CheckBalance>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        
        try:
            response = requests.post(
                'SOAP_ENDPOINT_URL',
                data=soap_body,
                headers={'Content-Type': 'text/xml'}
            )

            root = ET.fromstring(response.text)
            balance_data = root.find(".//{http://booking.us.org/}return").text
            balance_xml = ET.fromstring(balance_data)

            balance_list = []
            for airline in balance_xml.findall('Airline'):
                balance_list.append({
                    'airline_name': airline.find('AirlineName').text,
                    'agency_name': airline.find('AgencyName').text,
                    'balance_amount': airline.find('BalanceAmount').text
                })

            return Response({'balances': balance_list}, status=status.HTTP_200_OK)
   
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PassengerViewSet(viewsets.ModelViewSet):
    queryset = Passenger.objects.all()
    serializer_class = PassengerSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=['POST'], detail=False)
    def flight_availability(self, request):
        serializer = FlightAvailabilitySerializer(data=request.data)
        user = request.user
        data = serializer.validated_data
        sector_from = data['sector_from'].sector_code
        sector_to = data['sector_to'].sector_code

        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:FlightAvailability>
                    <strUserId>{user.user_id}</strUserId>
                    <strPassword>{user.api_password}</strPassword>
                    <strAgencyId>{user.agency_id}</strAgencyId>
                    <strSectorFrom>{sector_from}</strSectorFrom>
                    <strSectorTo>{sector_to}</strSectorTo>
                    <strFlightDate>{data['flight_date']}</strFlightDate>
                    <strReturnDate>{data.get('return_date', '')}</strReturnDate>
                    <strTripType>{data['trip_type']}</strTripType>
                    <strNationality>{data['nationality']}</strNationality>
                    <intAdult>{data['adult']}</intAdult>
                    <intChild>{data['child']}</intChild>
                    <strClientIP>{data['client_ip']}</strClientIP>
                </book:FlightAvailability>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        #TODO: Check flight details

    # @action(methods=['POST'],detail=False)
    # def reservation(self,request):