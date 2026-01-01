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