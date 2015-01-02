import json
import urllib, urllib2

from django.conf import settings

from helios.models import Poll

OAUTH2_REGISTRY = {}

def oauth2_module(cls):
    OAUTH2_REGISTRY[cls.type_id] = cls
    return cls

def get_oauth2_module(poll):
    return OAUTH2_REGISTRY.get(poll.oauth2_type)(poll)

class Oauth2Base(object):

    def __init__(self, poll):
        self.poll = poll
        self.code_post_data = {
            'response_type': 'code',
            'client_id': poll.oauth2_client_id,
            'redirect_uri': settings.OAUTH2_CALLBACK,
            'state': poll.uuid
        }

        self.exchange_data = {
            'client_id': poll.oauth2_client_id,
            'client_secret': poll.oauth2_client_secret,
            'redirect_uri': settings.OAUTH2_CALLBACK,
            'grant_type': 'authorization_code',
            }

    def get_code_url(self):
        code_data = self.code_post_data
        encoded_data = urllib.urlencode(self.code_post_data)
        url = "{}?{}".format(self.poll.oauth2_url, encoded_data)
        return url

    def can_exchange(self, request):
        if (request.GET.get('code') and request.GET.get('state') and
                request.session.get('oauth2_voter_uuid') and 
                request.session.get('oauth2_voter_email')):
            self.code = request.GET.get('code')
            self.session_email = request.session['oauth2_voter_email']
            self.voter_uuid = request.session.get('oauth2_voter_uuid')
            return True

    def get_exchange_url(self):
        self.exchange_data['code'] = self.code
        encoded_data = urllib.urlencode(self.exchange_data)
        return (self.exchange_url, encoded_data)

    def exchange(self, url):
        raise NotImplemented

@oauth2_module
class Oauth2Google(Oauth2Base):

    type_id = 'google'

    def __init__(self, poll):
        super(Oauth2Google, self).__init__(poll)
        self.code_post_data['scope'] = 'email'
        self.code_post_data['approval_prompt'] = 'force'
        self.exchange_url = 'https://accounts.google.com/o/oauth2/token'

    def set_login_hint(self, email):
        self.code_post_data['login_hint'] = email

    def exchange(self, url):
        response = urllib2.urlopen(url[0], url[1])
        data = json.loads(response.read())
        self.access_token = data['access_token']
        self.id_token = data['id_token']
        self.token_type = data['token_type']
        self.expires_in = data['expires_in']

    def confirm_email(self):
        url='https://www.googleapis.com/plus/v1/people/me'
        get_params = 'access_token={}'.format(self.access_token)
        get_url = '{}?{}'.format(url, get_params)
        response = urllib2.urlopen(get_url)
        data = json.loads(response.read())
        response_email = data['emails'][0]['value']
        if response_email == self.session_email:
            return True


class Oauth2FB(Oauth2Base):

    type_id = 'facebook'
    
    def __init__(self, poll):
        super(Oauth2FB, self).__init__(poll)
        self.code_post_data['scope'] = 'email'
        self.exchange_url = 'https://graph.facebook.com/oauth/access_token'

    def exchange(self, url):
        response = urllib2.urlopen(url[0], url[1])
        data = response.read()
        split_data = data.split('&')
        for item in split_data:
            if 'access_token' in item:
                self.access_token = item.split('=')[1]
            if 'expires' in item:
                self.expires = item.split('=')[1]

    def confirm_email(self):
        url = 'https://graph.facebook.com/v2.2/me'
        get_params = 'fields=email&access_token={}'.format(self.access_token)
        get_url = '{}?{}'.format(url, get_params)
        response = urllib2.urlopen(get_url)
        data = json.loads(response.read())
        response_email = data['email']
        if response_email == self.session_email:
            return True
