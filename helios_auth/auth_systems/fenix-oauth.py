from django.http import HttpResponseRedirecit
from helios_auth.models import AuthenticationExpired
from helios_auth.view_utils import render_template
from helios_auth.views import after
from helios_auth.models import User
import requests as req
import json

loginName = False
userToken = None

redirect_uri = http+public_ip+":"+port+"/mobile/userAuth" # this is the address of the page on this app
client_id= "570015174623394"
clientSecret = "BNSpLi3noPqnh6/AX2pBKXSOG2uVy+XZ+9MqcE3aq0QHWa5VOS350ofnhkcsMgqXeSRLX0iDSa5R6CzAfcu8NQ=="

fenixLoginpage= "https://fenix.tecnico.ulisboa.pt/oauth/userdialog?client_id=%s&redirect_uri=%s"
fenixacesstokenpage = 'https://fenix.tecnico.ulisboa.pt/oauth/access_token'
RequestPage = fenixLoginpage % (client_id, redirect_uri)


def login_fenix_oauth(request):   
    try:
        code = request.args['code']  
        payload = {'client_id': client_id, 'client_secret': clientSecret, 'redirect_uri' : redirect_uri, 'code' : code, 'grant_type': 'authorization_code'}
        response = req.post(fenixacesstokenpage, params = payload)
        if(response.status_code == 200):
            params = {'access_token': r_token['access_token']}
            
            global userToken
            userToken = r_token['access_token']
            request.session['access_token_fenix'] =r_token['access_token']
            
            return HttpResponseRedirect(reverse(url_names.AUTH_AFTER))
        else:
            return HttpResponseRedirect(RequestPage)
    except:
        return HttpResponseRedirect(RequestPage)


def get_auth_url(request, redirect_url = None):
    # the app redirects the user to the FENIX login page
    return HttpResponseRedirect(RequestPage)

def get_user_info_after_auth(request):
    token =  request.session['access_token_fenix'] 
    params = {'access_token': token}
    resp = req.get("https://fenix.tecnico.ulisboa.pt/api/fenix/v1/person", params = params)
    
    if (resp.status_code != 200):
        return HttpResponseRedirect(RequestPage)

    r_info = resp.json()
    del request.session['access_token_fenix']

    return {'type': 'fenix-oauth', 'user_id' : r_info["username"], 'name': r_info["name"], 'info': r_info["email"], 'token': userToken}


#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True

#^ matches the start of the string.
urlpatterns = [
  url(r'^fenix/login', login_fenix_oauth, name=FENIX_LOGIN),
]
