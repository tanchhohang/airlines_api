from decouple import config
import xml.etree.ElementTree as ET
import requests
from rest_framework.response import Response
from rest_framework import status

class UserAuthenticationMixin:

    def get_user_credentials(self):
        user = self.request.user
        return {
            'strUserId': user.user_id,
            'strPassword': user.api_password,
            'strAgencyId': user.agency_id
        }
    
    def get_user_id(self):
        return self.request.user.user_id
    
    def get_api_password(self):
        return self.request.user.api_password
    
    def get_agency_id(self):
        return self.request.user.agency_id

class SOAPRequestMixin:
    
    SOAP_ENDPOINT = config('SOAP_ENDPOINT_URL', default='SOAP_ENDPOINT_URL')
    SOAP_NAMESPACE = 'http://booking.us.org/'
    
    def make_soap_request(self, soap_body, timeout=30):
        try:
            response = requests.post(
                self.SOAP_ENDPOINT,
                data=soap_body,
                headers={'Content-Type': 'text/xml'},
                timeout=timeout
            )
            response.raise_for_status()
            return ET.fromstring(response.text)
        except:
            return None
    
    def extract_soap_return(self, root, tag_name='return'):
        try:
            return_element = root.find(f".//{{{self.SOAP_NAMESPACE}}}{tag_name}")
            if return_element is not None and return_element.text:
                return ET.fromstring(return_element.text.strip())
            return None
        except:
            return None
    
    def build_soap_envelope(self, method_name, params):
        param_strings = []
        for key, value in params.items():
            escaped_value = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            param_strings.append(f"<{key}>{escaped_value}</{key}>")
        
        return f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:book="{self.SOAP_NAMESPACE}">
            <soapenv:Body>
                <book:{method_name}>
                    {''.join(param_strings)}
                </book:{method_name}>
            </soapenv:Body>
        </soapenv:Envelope>
        """
    
    def handle_soap_error(self, message="SOAP request failed"):
        return Response(
            {'error': message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )