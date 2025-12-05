from .models import *
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import Mock, patch

class SectorAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            user_id='USER001',
            api_password='apipass123',
            agency_id='AGENCY001'
            )
        self.client.force_authenticate(self.user)
        self.sector1 = Sector.objects.create(sector_code = 'KTM', sector_name = 'Kathmandu')
        self.sector2 = Sector.objects.create(sector_code = 'PKR', sector_name = 'Pokhara')

        self.sector_list_url = reverse('sector-list')
        self.sector_code_url = reverse('sector-sector-code')

    def test_get_all_sectors(self):
        response = self.client.get(self.sector_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    
    def test_get_single_sector(self):
        sector_detail_url = reverse('sector-detail', kwargs={'pk': self.sector1.pk})
        response = self.client.get(sector_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sector_code'], 'KTM')
        self.assertEqual(response.data['sector_name'], 'Kathmandu')

    @patch('requests.post')
    def test_sector_code_return_sector_name_and_code(self, mock_post):
        # self.client.login(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:SectorCodeResponse>
                    <book:return><![CDATA[
                        <FlightSector>
                            <Sector>
                                <SectorCode>KTM</SectorCode>
                                <SectorName>KATHMANDU</SectorName>
                            </Sector>
                            <Sector>
                                <SectorCode>PKR</SectorCode>
                                <SectorName>POKHARA</SectorName>
                            </Sector>
                        </FlightSector>
                    ]]></book:return>
                </book:SectorCodeResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response
        
        response = self.client.post(self.sector_code_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['sectors']), 2)

class AirlineAPITestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass',
            user_id='ADMIN001',
            api_password='adminapi123',
            agency_id='AGENCY001'
        )
        self.normal_user = User.objects.create_user(
            username='user1',
            password='userpass',
            user_id='USER001',
            api_password='userapi123',
            agency_id='AGENCY001'
        )

        self.airline_buddha = Airline.objects.create( airline_id='U4',airline_name='Buddha Air', fare=5000.00)
        self.airline_yeti = Airline.objects.create(airline_id='YT', airline_name='Yeti Airlines',fare=5000.00)

        self.airline_list_url = reverse('airline-list')
        self.check_balance_url = reverse('airline-check-balance')

    def test_get_airlines_requires_authentication(self):
        response = self.client.get(self.airline_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_authenticated_user_can_get_airlines(self):
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(self.airline_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_single_airline(self):
        self.client.force_authenticate(user=self.normal_user)
        airline_detail_url = reverse('airline-detail', kwargs={'pk': self.airline_buddha.pk})
        response = self.client.get(airline_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['airline_name'], 'Buddha Air')
        self.assertEqual(response.data['airline_id'], 'U4')

    @patch('requests.post')
    def test_check_balance_returns_correct_structure(self, mock_post):
        self.client.force_authenticate(user=self.normal_user)

        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:CheckBalanceResponse>
                    <book:return><![CDATA[
                        <Balance>
                            <Airline>
                                <AirlineName>Buddha Air</AirlineName>
                                <AgencyName>TestAgency</AgencyName>
                                <BalanceAmount>10000000.00</BalanceAmount>
                            </Airline>
                        </Balance>
                    ]]></book:return>
                </book:CheckBalanceResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        mock_post.return_value = mock_response

        data = {'airline_id': 'U4'}
        response = self.client.post(self.check_balance_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('balances', response.data)
        self.assertEqual(len(response.data['balances']), 1)

class ReservationAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            user_id='USER001',
            api_password='apipass123',
            agency_id='AGENCY001'
        )

        self.reservation_url = reverse('booking-test-reservation')

    @patch('requests.post')
    def test_reservation_success(self, mock_post):
        self.client.force_authenticate(user=self.user)

        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:ReservationResponse>
                    <book:return><![CDATA[
                        <PNRDetail>
                            <AirlineID>U4</AirlineID>
                            <FlightId>123</FlightId>
                            <PNRNO>PNR001</PNRNO>
                            <ReservationStatus>HK</ReservationStatus>
                            <TTLDate>2025-01-01</TTLDate>
                            <TTLTime>12:00</TTLTime>
                        </PNRDetail>
                    ]]></book:return>
                </book:ReservationResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {
            "flight_id": "123",
            "return_flight_id": ""
        }

        response = self.client.post(self.reservation_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('reservation info', response.data)
        self.assertEqual(response.data['reservation info']['pnr_no'], 'PNR001')
        self.assertEqual(response.data['reservation info']['reservation_status'], 'HK')

class FlightAvailabilityAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            user_id='USER001', api_password='apipass123', agency_id='AGENCY001'
        )
        self.sector_ktm = Sector.objects.create(sector_code='KTM', sector_name='Kathmandu')
        self.sector_pkr = Sector.objects.create(sector_code='PKR', sector_name='Pokhara')
        self.flight_availability_url = reverse('booking-test-flight-availability')

    @patch('requests.post')
    def test_flight_availability_one_way(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" book="" xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:FlightAvailabilityResponse>
                    <book:return><![CDATA[
                    <Flightavailability>
                        <Outbound>
                            <Availability>
                                <Airline>U4</Airline>
                                <AirlineLogo>http://test.com/U4.jpg</AirlineLogo>
                                <FlightDate>30-SEP-2025</FlightDate>
                                <FlightNo>U4123</FlightNo>
                                <Departure>KATHMANDU</Departure>
                                <DepartureTime>10:00</DepartureTime>
                                <Arrival>POKHARA</Arrival>
                                <ArrivalTime>10:30</ArrivalTime>
                                <AircraftType>TEST</AircraftType>
                                <Adult>1</Adult>
                                <Child>0</Child>
                                <Infant>0</Infant>
                                <FlightId>abc-123-def</FlightId>
                                <FlightClassCode>Y</FlightClassCode>
                                <Currency>NPR</Currency>
                                <AdultFare>5000</AdultFare>
                                <ChildFare>3500</ChildFare>
                                <InfantFare>500</InfantFare>
                                <FuelSurcharge>1500</FuelSurcharge>
                                <Tax>200</Tax>
                                <Refundable>T</Refundable>
                                <FreeBaggage>20KG</FreeBaggage>
                                <AgencyCommission>500</AgencyCommission>
                            </Availability>
                        </Outbound>
                        <Inbound/>
                    </Flightavailability>]]></book:return>
                </book:FlightAvailabilityResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {
            'sector_from': self.sector_ktm.pk,
            'sector_to': self.sector_pkr.pk,
            'flight_date': '30-09-2025',
            'trip_type': 'O',
            'nationality': 'NP',
            'adult': 1,
            'child': 0,
            'client_ip': '127.0.0.1'
        }
        response = self.client.post(self.flight_availability_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('outbound_flights', response.data)
        self.assertEqual(len(response.data['outbound_flights']), 1)
        self.assertEqual(response.data['outbound_flights'][0]['flight_id'], 'abc-123-def')
        self.assertEqual(response.data['outbound_flights'][0]['total_adult_fare'], 6700)  # 5000+1500+200

    @patch('requests.post')
    def test_flight_availability_round_trip(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
         <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" book="" xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:FlightAvailabilityResponse>
                    <book:return><![CDATA[
                    <Flightavailability>
                        <Outbound>
                            <Availability>
                                <Airline>U4</Airline>
                                <AirlineLogo>http://test.com/U4.jpg</AirlineLogo>
                                <FlightDate>30-SEP-2025</FlightDate>
                                <FlightNo>U4123</FlightNo>
                                <Departure>KATHMANDU</Departure>
                                <DepartureTime>10:00</DepartureTime>
                                <Arrival>POKHARA</Arrival>
                                <ArrivalTime>10:30</ArrivalTime>
                                <AircraftType>ATR72</AircraftType>
                                <Adult>1</Adult><Child>0</Child><Infant>0</Infant>
                                <FlightId>outbound-123</FlightId>
                                <FlightClassCode>Y</FlightClassCode>
                                <Currency>NPR</Currency>
                                <AdultFare>5000</AdultFare>
                                <ChildFare>3500</ChildFare>
                                <InfantFare>500</InfantFare>
                                <FuelSurcharge>1500</FuelSurcharge>
                                <Tax>200</Tax>
                                <Refundable>T</Refundable>
                                <FreeBaggage>20KG</FreeBaggage>
                                <AgencyCommission>500</AgencyCommission>
                            </Availability>
                        </Outbound>
                        <Inbound>
                            <Availability>
                                <Airline>U4</Airline>
                                <FlightDate>05-OCT-2025</FlightDate>
                                <FlightNo>U4124</FlightNo>
                                <Departure>POKHARA</Departure>
                                <DepartureTime>14:00</DepartureTime>
                                <Arrival>KATHMANDU</Arrival>
                                <ArrivalTime>14:30</ArrivalTime>
                                <FlightId>inbound-456</FlightId>
                                <AdultFare>5000</AdultFare>
                                <ChildFare>3500</ChildFare>
                                <FuelSurcharge>1500</FuelSurcharge>
                                <Tax>200</Tax>
                            </Availability>
                        </Inbound>
                    </Flightavailability>]]></book:return>
                </book:FlightAvailabilityResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {
            'sector_from': self.sector_ktm.pk,
            'sector_to': self.sector_pkr.pk,
            'flight_date': '30-09-2025',
            'return_date': '05-10-2025',
            'trip_type': 'R',
            'nationality': 'NP',
            'adult': 1,
            'child': 0,
            'client_ip': '127.0.0.1'
        }
        response = self.client.post(self.flight_availability_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('outbound_flights', response.data)
        self.assertIn('inbound_flights', response.data)
        self.assertEqual(len(response.data['inbound_flights']), 1)

class IssueTicketAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            user_id='USER001', api_password='apipass123', agency_id='AGENCY001'
        )
        self.issue_ticket_url = reverse('booking-test-issue-ticket')

    @patch('requests.post')
    def test_issue_ticket(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" book="" xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:IssueTicketResponse>
                    <book:Itinerary>
                        <book:Passenger>
                            <book:Airline>U4</book:Airline>
                            <book:PnrNo>ABC123</book:PnrNo>
                            <book:Title>MR</book:Title>
                            <book:Gender>M</book:Gender>
                            <book:FirstName>TANCHHO</book:FirstName>
                            <book:LastName>LIMBU</book:LastName>
                            <book:PaxType>ADULT</book:PaxType>
                            <book:Nationality>NP</book:Nationality>
                            <book:IssueFrom>AGENCY001</book:IssueFrom>
                            <book:AgencyName>Test Agency</book:AgencyName>
                            <book:IssueDate>21-NOV-2025</book:IssueDate>
                            <book:IssueBy>USER001</book:IssueBy>
                            <book:FlightNo>U4123</book:FlightNo>
                            <book:FlightDate>05-OCT-2025</book:FlightDate>
                            <book:Departure>KTM</book:Departure>
                            <book:FlightTime>1000</book:FlightTime>
                            <book:TicketNo>9999999999</book:TicketNo>
                            <book:BarCodeValue>5555555</book:BarCodeValue>
                            <book:BarcodeImage></book:BarcodeImage>
                            <book:Arrival>PKR</book:Arrival>
                            <book:ArrivalTime>10:30</book:ArrivalTime>
                            <book:Sector>KTM-PKR</book:Sector>
                            <book:ClassCode>Y</book:ClassCode>
                            <book:Currency>NPR</book:Currency>
                            <book:Fare>5000</book:Fare>
                            <book:Surcharge>1500</book:Surcharge>
                            <book:TaxCurrency>NPR</book:TaxCurrency>
                            <book:Tax>200</book:Tax>
                            <book:CommissionAmount>500</book:CommissionAmount>
                            <book:Refundable>Refundable</book:Refundable>
                            <book:ReportingTime>One hour in adnvace</book:ReportingTime>
                            <book:FreeBaggage>20KG</book:FreeBaggage>
                        </book:Passenger>
                    </book:Itinerary>
                </book:IssueTicketResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {
            'flight_id': 'abc-123-def',
            'return_flight_id': '',
            'contact_name': 'TANCHHO LIMBU',
            'contact_email': 'a@b.com',
            'contact_mobile': '9999999999',
            'passenger_detail': [{
                'pax_type': 'ADULT',
                'title': 'MR',
                'gender': 'M',
                'first_name': 'TANCHHO',
                'last_name': 'LIMBU',
                'nationality': 'NP',
                'remarks': 'N/A'
            }]
        }
        response = self.client.post(self.issue_ticket_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('itinerary', response.data)
        self.assertEqual(response.data['itinerary'][0]['ticket_no'], '9999999999')
        self.assertEqual(response.data['itinerary'][0]['pnr_no'], 'ABC123')



class GetItineraryAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            user_id='USER001', api_password='apipass123', agency_id='AGENCY001'
        )
        self.get_itinerary_url = reverse('booking-test-get-itinerary')

    @patch('requests.post')
    def test_get_itinerary_by_pnr(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:GetItineraryResponse>
                    <book:Itinerary><![CDATA[
                        <Itinerary>
                            <Passenger>
                                <Airline>U4</Airline>
                                <PnrNo>ABC123</PnrNo>
                                <Title>MR</Title>
                                <Gender>M</Gender>
                                <FirstName>TANCHHO</FirstName>
                                <LastName>LIMBU</LastName>
                                <PaxType>ADULT</PaxType>
                                <Nationality>NP</Nationality>
                                <TicketNo>9999999999</TicketNo>
                                <FlightNo>U4123</FlightNo>
                                <FlightDate>05-OCT-2025</FlightDate>
                                <Departure>KTM</Departure>
                                <Arrival>PKR</Arrival>
                            </Passenger>
                        </Itinerary>
                    ]]></book:Itinerary>
                </book:GetItineraryResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {
            'pnr_no': 'ABC123',
            'ticket_no': '',
            'airline_id': 'U4'
        }

        response = self.client.post(self.get_itinerary_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('itinerary', response.data)

    @patch('requests.post')
    def test_get_itinerary_by_ticket_no(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:GetItineraryResponse>
                    <book:Itinerary><![CDATA[
                        <Itinerary>
                            <Passenger>
                                <Airline>U4</Airline>
                                <PnrNo>ABC123</PnrNo>
                                <TicketNo>9999999999</TicketNo>
                                <FirstName>TANCHHO</FirstName>
                                <LastName>LIMBU</LastName>
                            </Passenger>
                        </Itinerary>
                    ]]></book:Itinerary>
                </book:GetItineraryResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {
            'pnr_no': '',
            'ticket_no': '9999999999',
            'airline_id': 'U4'
        }

        response = self.client.post(self.get_itinerary_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('itinerary', response.data)


class GetFlightDetailAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            user_id='USER001', api_password='apipass123', agency_id='AGENCY001'
        )
        self.get_flight_detail_url = reverse('booking-test-get-flight-detail')

    @patch('requests.post')
    def test_get_flight_detail_success(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:GetFlightDetailResponse>
                    <book:Availability>
                        <Airline>U4</Airline>
                        <FlightNo>U4123</FlightNo>
                        <FlightDate>30-SEP-2025</FlightDate>
                        <Departure>KATHMANDU</Departure>
                        <DepartureTime>10:00</DepartureTime>
                        <Arrival>POKHARA</Arrival>
                        <ArrivalTime>10:30</ArrivalTime>
                        <FlightId>abc-123-def</FlightId>
                        <AdultFare>5000</AdultFare>
                        <ChildFare>3500</ChildFare>
                        <FuelSurcharge>1500</FuelSurcharge>
                        <Tax>200</Tax>
                        <Currency>NPR</Currency>
                    </book:Availability>
                </book:GetFlightDetailResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {'flight_id': 'abc-123-def'}
        response = self.client.post(self.get_flight_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('flight_detail', response.data)


class GetPnrDetailAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            user_id='USER001', api_password='apipass123', agency_id='AGENCY001'
        )
        self.get_pnr_detail_url = reverse('booking-test-get-pnr-detail')

    @patch('requests.post')
    def test_get_pnr_detail_returns_url(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:GetPnrDetailResponse>
                    <book:return>https://booking-system.com/pnr/ABC123</book:return>
                </book:GetPnrDetailResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = mock_response

        data = {
            'pnr_no': 'ABC123',
            'last_name': 'LIMBU'
        }

        response = self.client.post(self.get_pnr_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('pnr_maintenance_url', response.data)
        self.assertEqual(response.data['pnr_maintenance_url'], 'https://booking-system.com/pnr/ABC123')


class SalesReportAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            user_id='USER001', api_password='apipass123', agency_id='AGENCY001'
        )
        self.sales_report_url = reverse('booking-test-sales-report')

    @patch('requests.post')
    def test_sales_report_success(self, mock_post):
        self.client.force_authenticate(user=self.user)
        mock_response = Mock()
        mock_response.text = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:book="http://booking.us.org/">
            <soapenv:Body>
                <book:SalesReportResponse>
                    <book:SalesSummary>
                        <TicketDetail>
                            <PnrNo>ABC123</PnrNo>
                            <Airline>U4</Airline>
                            <IssueDate>21-NOV-2025</IssueDate>
                            <FlightNo>U4123</FlightNo>
                            <FlightDate>30-SEP-2025</FlightDate>
                            <SectorPair>KTM-PKR</SectorPair>
                            <ClassCode>Y</ClassCode>
                            <TicketNo>9999999999</TicketNo>
                            <PassengerName>TANCHHO LIMBU</PassengerName>
                            <Nationality>NP</Nationality>
                            <PaxType>ADULT</PaxType>
                            <Currency>NPR</Currency>
                            <Fare>5000</Fare>
                            <FSC>1500</FSC>
                            <TAX>200</TAX>
                        </TicketDetail>
                    </book:SalesSummary>
                </book:SalesReportResponse>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        data = {
        'from_date': '01-NOV-2025',
        'to_date': '30-NOV-2025'
        }

        response = self.client.post(self.sales_report_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sales_report', response.data)
        self.assertIn('total_tickets', response.data)
        self.assertEqual(len(response.data['sales_report']), 1)
        self.assertEqual(response.data['total_tickets'], 1)
        
        ticket = response.data['sales_report'][0]
        self.assertEqual(ticket['pnr_no'], 'ABC123')
        self.assertEqual(ticket['airline'], 'U4')
        self.assertEqual(ticket['ticket_no'], '9999999999')
        self.assertEqual(ticket['passenger_name'], 'TANCHHO LIMBU')
        self.assertEqual(ticket['fare'], '5000')
        self.assertEqual(ticket['fsc'], '1500')
        self.assertEqual(ticket['tax'], '200')