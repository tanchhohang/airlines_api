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
    permission_classes = [IsAuthenticated]

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
            balance_data = root.find(".//{http://booking.us.org/}return").text.strip()
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

        #TODO: Parse XML to JSON
        try:
            response = requests.post(
                'soapurl',
                data=soap_body,
                headers={'Content-Type': 'text/xml'}
            )
            root = ET.fromstring(response.text)
            flight_xml = ET.fromstring(root.find(".//{http://booking.us.org/}return").text)
            
            outbound = flight_xml.find('Outbound')
            inbound = flight_xml.find('Inbound')
            
            outbound_flights = []
            for a in (outbound.findall('Availability') if outbound is not None else []):
                adult_fare = float(a.find('AdultFare').text)
                child_fare = float(a.find('ChildFare').text)
                fuel_surcharge = float(a.find('FuelSurcharge').text)
                tax = float(a.find('Tax').text)
                child_tax_adj = float(a.find('ChildTaxAdjustment').text) if a.find('ChildTaxAdjustment') is not None else 0
                
                outbound_flights.append({
                    'airline': a.find('Airline').text,
                    'airline_logo': a.find('AirlineLogo').text,
                    'flight_date': a.find('FlightDate').text,
                    'flight_no': a.find('FlightNo').text,
                    'departure': a.find('Departure').text,
                    'departure_time': a.find('DepartureTime').text,
                    'arrival': a.find('Arrival').text,
                    'arrival_time': a.find('ArrivalTime').text,
                    'aircraft_type': a.find('AircraftType').text,
                    'adult': int(a.find('Adult').text),
                    'child': int(a.find('Child').text),
                    'infant': int(a.find('Infant').text),
                    'flight_id': a.find('FlightId').text,
                    'flight_class_code': a.find('FlightClassCode').text,
                    'currency': a.find('Currency').text,
                    'adult_fare': adult_fare,
                    'child_fare': child_fare,
                    'infant_fare': float(a.find('InfantFare').text),
                    'fuel_surcharge': fuel_surcharge,
                    'tax': tax,
                    'child_tax_adjustment': child_tax_adj,
                    'total_adult_fare': adult_fare + fuel_surcharge + tax,
                    'total_child_fare': child_fare + fuel_surcharge + tax + child_tax_adj,
                    'refundable': a.find('Refundable').text,
                    'free_baggage': a.find('FreeBaggage').text,
                    'agency_commission': float(a.find('AgencyCommission').text),
                    'child_commission': float(a.find('ChildCommission').text) if a.find('ChildCommission') is not None else 0,
                })
            
            inbound_flights = []
            for a in (inbound.findall('Availability') if inbound is not None else []):
                adult_fare = float(a.find('AdultFare').text)
                child_fare = float(a.find('ChildFare').text)
                fuel_surcharge = float(a.find('FuelSurcharge').text)
                tax = float(a.find('Tax').text)
                child_tax_adj = float(a.find('ChildTaxAdjustment').text) if a.find('ChildTaxAdjustment') is not None else 0
                
                inbound_flights.append({
                    'airline': a.find('Airline').text,
                    'flight_date': a.find('FlightDate').text,
                    'flight_no': a.find('FlightNo').text,
                    'departure': a.find('Departure').text,
                    'departure_time': a.find('DepartureTime').text,
                    'arrival': a.find('Arrival').text,
                    'arrival_time': a.find('ArrivalTime').text,
                    'flight_id': a.find('FlightId').text,
                    'adult_fare': adult_fare,
                    'child_fare': child_fare,
                    'fuel_surcharge': fuel_surcharge,
                    'tax': tax,
                    'child_tax_adjustment': child_tax_adj,
                    'total_adult_fare': adult_fare + fuel_surcharge + tax,
                    'total_child_fare': child_fare + fuel_surcharge + tax + child_tax_adj,
                })
            
            return Response({
                'outbound_flights': outbound_flights,
                'inbound_flights': inbound_flights
            }, status=status.HTTP_200_OK)
            
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
    @action(methods=['POST'],detail=False)
    def reservation(self,request):
        serializer = ReservationSerializer(data= request.data)
        serializer.is_valid(raise_exception=True) 
        data = serializer.validated_data

        soap_body=f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:Reservation>
                    <strFlightId>{data['flight_id']}</strFlightId>
                    <strReturnFlightId>{data.get('return_flight_id', '')}</strReturnFlightId>
                </book:Reservation>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        try:
            response = requests.post(
                'soapurl',
                data = soap_body,
                headers={'Content-Type': 'text/xml'},
            )

            root = ET.fromstring(response.text)
            pnr_detail = root.find(".//{http://booking.us.org/}return") 
            pnr_element = ET.fromstring(pnr_detail.text)                
            reservation_info = {
                'airline_id':pnr_element.find('AirlineID').text,
                'flight_id': pnr_element.find('FlightId').text,
                'pnr_no': pnr_element.find('PNRNO').text,
                'reservation_status': pnr_element.find('ReservationStatus').text,
                'ttl_date': pnr_element.find('TTLDate').text,
                'ttl_time': pnr_element.find('TTLTime').text,
            }
            return Response({'reservation info': reservation_info}, status=status.HTTP_200_OK)
        except Exception as e:
            print("RESERVATION ERROR:", e)
            raise
    
    # @action(methods=['POST'], detail=False)
    # def issue_ticket(self.request):


    @action(methods=['POST'], detail=False)
    def get_itinerary(self, request):
        pnr_no = request.data.get('pnr_no', '')
        ticket_no = request.data.get('ticket_no', '')
        airline_id = request.data.get('airline_id', '')

        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:GetItinerary>
                    <strPnoNo>{pnr_no}</strPnoNo>
                    <strTicketNo>{ticket_no}</strTicketNo>
                    <strAgencyId>{airline_id}</strAgencyId>
                </book:GetItinerary>
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
            itinerary_root = root.find(".//{http://booking.us.org/}Itinerary")
            itinerary  = ET.fromstring(itinerary_root)
            passengers = []

            for passenger in itinerary.findall('Passenger'):
                    passengers.append(self._parse_passenger_itinerary(passenger))

            return Response({'itinerary': passengers}, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(methods=['POST'], detail=False)
    def get_flight_detail(self, request):
        user = request.user
        flight_id = request.data.get('flight_id')
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:GetFlightDetail>
                    <strUserId>{user.user_id}</strUserId>
                    <strFlightId>{flight_id}</strFlightId>
                </book:GetFlightDetail>
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
            availability = root.find(".//{http://booking.us.org/}Availability")
            flight_detail = self._parse_flight_availability(availability)
            return Response({'flight_detail': flight_detail}, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    @action(methods=['POST'], detail=False)
    def get_pnr_detail(self, request):
        user = request.user
        pnr_no = request.data.get('pnr_no')
        last_name = request.data.get('last_name')
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:GetPnrDetail>
                    <strUserId>{user.user_id}</strUserId>
                    <strPassword>{user.api_pasword}</strPassword>
                    <strAgencyId>{user.agency_id}</strAgencyId>
                    <strPnrNo>{pnr_no}</strPnrNo>
                    <strLastName>{last_name}</strLastName>
                </book:GetPnrDetail>
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
            pnr_detail = root.find(".//{http://booking.us.org/}return")
            return Response({'pnr_maintenance_url': pnr_detail.text}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['POST'], detail=False)
    def sales_report(self, request):
        user = request.user
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:SalesReport>
                    <strUserId>{user.user_id}</strUserId>
                    <strPassword>{user.api_pasword}</strPassword>
                    <strAgencyId>{user.agency_id}</strAgencyId>
                    <strPnrNo>{from_date}</strPnrNo>
                    <strTicketNo>{to_date}</strTicketNo>
                </book:SalesReport>
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
            sales_summary = root.find(".//{http://booking.us.org/}SalesSummary")
            tickets = []
            for ticket_detail in sales_summary.findall('TicketDetail'):
                tickets.append({
                    'pnr_no': ticket_detail.find('PnrNo').text,
                    'airline': ticket_detail.find('Airline').text,
                    'issue_date': ticket_detail.find('IssueDate').text,
                    'flight_no': ticket_detail.find('FlightNo').text,
                    'flight_date': ticket_detail.find('FlightDate').text,
                    'sector_pair': ticket_detail.find('SectorPair').text,
                    'class_code': ticket_detail.find('ClassCode').text,
                    'ticket_no': ticket_detail.find('TicketNo').text,
                    'passenger_name': ticket_detail.find('PassengerMame').text,
                    'nationality': ticket_detail.find('Nationality').text,
                    'pax_type': ticket_detail.find('PaxType').text,
                    'currency': ticket_detail.find('Currency').text,
                    'fare': ticket_detail.find('Fare').text,
                    'fsc': ticket_detail.find('FSC').text,
                    'tax': ticket_detail.find('TAX').text,
                })
            
            return Response({
                'sales_report': tickets,
                'total_tickets': len(tickets)
            }, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)