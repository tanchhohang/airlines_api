import requests, json
from django.shortcuts import render
from .serializer import *
from rest_framework import viewsets, filters
from rest_framework.permissions import(
    IsAuthenticated,
    AllowAny
)
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import *
from .serializer import *
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
import xml.etree.ElementTree as ET
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.vary import vary_on_headers
from .mixins import UserAuthenticationMixin, SOAPRequestMixin
from django.core.cache import cache


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Booking.objects.select_related(
        'user',
        'airline', 
        'departure',
        'arrival'
    ).prefetch_related(
        'passengers'
    )
    serializer_class = UserSerializer

class SectorViewSet(UserAuthenticationMixin, SOAPRequestMixin, viewsets.ReadOnlyModelViewSet):
    queryset= Sector.objects.all()  
    serializer_class = SectorSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60 * 15, key_prefix='sector_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        import time
        time.sleep(2)
        return super().get_queryset()

    @action(methods=['POST'],detail=False)
    def sector_code(self,request):
        user_creds = self.get_user_credentials()
        
        soap_body = self.build_soap_envelope('SectorCode', user_creds)
        root = self.make_soap_request(soap_body)
        if root is None:
            return self.handle_soap_error("Failed to get sector codes")
        sector_data = self.extract_soap_return(root)

        if sector_data is None:
            return self.handle_soap_error("Failed to parse sector data")

        sector_list = []
        for sector in sector_data.findall('Sector'):
            code = sector.find('SectorCode').text
            name = sector.find('SectorName').text
            
            sector_obj, created = Sector.objects.update_or_create(
                sector_code=code,
                defaults={"sector_name": name}
            )
            sector_list.append(sector_obj)

        serializer = SectorSerializer(sector_list, many=True)
        return Response({'sectors': serializer.data})

class AirlinesViewSet(UserAuthenticationMixin, SOAPRequestMixin, viewsets.ReadOnlyModelViewSet):  # CHANGED: Added SOAPRequestMixin
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60 * 15, key_prefix='airline_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(methods=['POST'],detail=False)
    def check_balance(self,request):
        user_creds = self.get_user_credentials()
        airline_id = request.data.get('airline_id')

        params = {**user_creds, 'strAirlineId': airline_id}
        soap_body = self.build_soap_envelope('CheckBalance', params)

        root = self.make_soap_request(soap_body)
        if root is None:
            return self.handle_soap_error("Failed to check balance")

        balance_data = self.extract_soap_return(root)
        if balance_data is None:
            return self.handle_soap_error("Failed to parse balance data")

        balance_list = []
        for airline in balance_data.findall('Airline'):
            balance_list.append({
                'airline_name': airline.find('AirlineName').text,
                'agency_name': airline.find('AgencyName').text,
                'balance_amount': airline.find('BalanceAmount').text
            })

        return Response({'balances': balance_list}, status=status.HTTP_200_OK)


class PassengerViewSet(viewsets.ModelViewSet):
    queryset = Passenger.objects.all()
    serializer_class = PassengerSerializer

class BookingViewSet(UserAuthenticationMixin, SOAPRequestMixin, viewsets.ModelViewSet):  # CHANGED: Added SOAPRequestMixin
    queryset = Passenger.objects.select_related(
        'booking',
        'booking__airline',
        'booking__departure',
        'booking__arrival'
    )
    serializer_class = BookingSerializer

    @action(methods=['POST'], detail=False)
    def flight_availability(self, request):
        serializer = FlightAvailabilitySerializer(data=request.data)
        user_creds = self.get_user_credentials()
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        sector_from = data['sector_from'].sector_code
        sector_to = data['sector_to'].sector_code

        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:FlightAvailability>
                    <strUserId>{user_creds['strUserId']}</strUserId>
                    <strPassword>{user_creds['strPassword']}</strPassword>
                    <strAgencyId>{user_creds['strAgencyId']}</strAgencyId>
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

        params = {
            'strFlightId': data['flight_id'],
            'strReturnFlightId': data.get('return_flight_id', '')
        }
        soap_body = self.build_soap_envelope('Reservation', params)

        root = self.make_soap_request(soap_body)
        if root is None:
            return self.handle_soap_error("Failed to make reservation")

        pnr_detail = self.extract_soap_return(root)
        if pnr_detail is None:
            return self.handle_soap_error("Failed to parse reservation data")
        
        reservation_info = {
            'airline_id': pnr_detail.find('AirlineID').text,
            'flight_id': pnr_detail.find('FlightId').text,
            'pnr_no': pnr_detail.find('PNRNO').text,
            'reservation_status': pnr_detail.find('ReservationStatus').text,
            'ttl_date': pnr_detail.find('TTLDate').text,
            'ttl_time': pnr_detail.find('TTLTime').text,
        }
        return Response({'reservation info': reservation_info}, status=status.HTTP_200_OK)
    
    @action(methods=['POST'], detail=False)
    def issue_ticket(self,request):
        serializer = IssueTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        xml_parts = ['<?xml version="1.0" ?><PassengerDetail>']
        for pax in data['passenger_detail']:
            xml_parts.append(f"""<Passenger>
                <PaxType>{pax['pax_type']}</PaxType>
                <Title>{pax['title']}</Title>
                <Gender>{pax['gender']}</Gender>
                <FirstName>{pax['first_name']}</FirstName>
                <LastName>{pax['last_name']}</LastName>
                <Nationality>{pax['nationality']}</Nationality>
                <PaxRemarks>{pax.get('remarks', 'N/A')}</PaxRemarks>
            </Passenger>""")
        xml_parts.append('</PassengerDetail>')
        passenger_xml = ''.join(xml_parts)
        
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:IssueTicket>
                    <strFlightId>{data['flight_id']}</strFlightId>
                    <strReturnFlightId>{data.get('return_flight_id', '')}</strReturnFlightId>
                    <strContactName>{data['contact_name']}</strContactName>
                    <strContactEmail>{data['contact_email']}</strContactEmail>
                    <strContactMobile>{data['contact_mobile']}</strContactMobile>
                    <strPassengerDetail><![CDATA[{passenger_xml}]]></strPassengerDetail>
                </book:IssueTicket>
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
            ns = {'book': 'http://booking.us.org/'}
            itinerary = root.find('.//book:Itinerary', ns)
            passengers = []

            for p in itinerary.findall('book:Passenger', ns):
                passengers.append({
                    'airline': p.find('book:Airline', ns).text,
                    'pnr_no': p.find('book:PnrNo', ns).text,
                    'title': p.find('book:Title', ns).text,
                    'gender': p.find('book:Gender', ns).text,
                    'first_name': p.find('book:FirstName', ns).text,
                    'last_name': p.find('book:LastName', ns).text,
                    'pax_type': p.find('book:PaxType', ns).text,
                    'nationality': p.find('book:Nationality', ns).text,
                    'issue_from': p.find('book:IssueFrom', ns).text,
                    'agency_name': p.find('book:AgencyName', ns).text,
                    'issue_date': p.find('book:IssueDate', ns).text,
                    'issue_by': p.find('book:IssueBy', ns).text,
                    'flight_no': p.find('book:FlightNo', ns).text,
                    'flight_date': p.find('book:FlightDate', ns).text,
                    'departure': p.find('book:Departure', ns).text,
                    'flight_time': p.find('book:FlightTime', ns).text,
                    'ticket_no': p.find('book:TicketNo', ns).text,
                    'barcode_value': p.find('book:BarCodeValue', ns).text,
                    'barcode_image': p.find('book:BarcodeImage', ns).text,
                    'arrival': p.find('book:Arrival', ns).text,
                    'arrival_time': p.find('book:ArrivalTime', ns).text,
                    'sector': p.find('book:Sector', ns).text,
                    'class_code': p.find('book:ClassCode', ns).text,
                    'currency': p.find('book:Currency', ns).text,
                    'fare': p.find('book:Fare', ns).text,
                    'surcharge': p.find('book:Surcharge', ns).text,
                    'tax_currency': p.find('book:TaxCurrency', ns).text,
                    'tax': p.find('book:Tax', ns).text,
                    'commission_amount': p.find('book:CommissionAmount', ns).text,
                    'refundable': p.find('book:Refundable', ns).text,
                    'reporting_time': p.find('book:ReportingTime', ns).text,
                    'free_baggage': p.find('book:FreeBaggage', ns).text,
                })
            
            return Response({'itinerary': passengers, 'message': 'Ticket issued successfully'}, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        user_creds = self.get_user_credentials()
        pnr_no = request.data.get('pnr_no')
        last_name = request.data.get('last_name')
        
        params = {**user_creds, 'strPnrNo': pnr_no, 'strLastName': last_name}
        soap_body = self.build_soap_envelope('GetPnrDetail', params)

        root = self.make_soap_request(soap_body)
        if root is None:
            return self.handle_soap_error("Failed to get PNR detail")
        
        pnr_detail = root.find(".//{http://booking.us.org/}return")
        return Response({'pnr_maintenance_url': pnr_detail.text if pnr_detail is not None else ''}, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def sales_report(self, request):
        user_creds = self.get_user_credentials()
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')

        cache_key = f"sales_{user_creds['strUserId']}_{from_date}_{to_date}" 
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        
        params = {**user_creds, 'strPnrNo': from_date, 'strTicketNo': to_date}
        soap_body = self.build_soap_envelope('SalesReport', params)

        root = self.make_soap_request(soap_body)
        if root is None:
            return self.handle_soap_error("Failed to fetch sales report")
        
        sales_summary = root.find(".//{http://booking.us.org/}SalesSummary")
        if sales_summary is None:
            return self.handle_soap_error("Failed to parse sales report")
        
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
                'passenger_name': ticket_detail.find('PassengerName').text,
                'nationality': ticket_detail.find('Nationality').text,
                'pax_type': ticket_detail.find('PaxType').text,
                'currency': ticket_detail.find('Currency').text,
                'fare': ticket_detail.find('Fare').text,
                'fsc': ticket_detail.find('FSC').text,
                'tax': ticket_detail.find('TAX').text,
            })

        report_data = {
            'sales_report': tickets,
            'total_tickets': len(tickets)
        }

        cache.set(cache_key, report_data, timeout=900)
        
        return Response(report_data, status=status.HTTP_200_OK) 