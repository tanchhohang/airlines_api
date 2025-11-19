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

        self.reservation_url = reverse('booking-reservation')

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
                            <ReservationStatus>CONFIRMED</ReservationStatus>
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
        self.assertEqual(response.data['reservation info']['reservation_status'], 'CONFIRMED')