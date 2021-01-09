import requests as req
import json
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.conf.urls import url
from django.conf import settings

client_id = settings.FENIX_CLIENT_ID
clientSecret = settings.FENIX_CLIENT_SECRET
redirect_uri = settings.URL_HOST + settings.FENIX_REDIRECT_URL_PATH

# Note, make sure that you exported the URL_HOST variable, otherwise localhost will be the default
print("SETUP redirect_uri:", redirect_uri) # debug

fenixLoginpage = settings.FENIX_LOGIN
fenixacesstokenpage = settings.FENIX_URL_TOKEN
RequestPage = fenixLoginpage % (client_id, redirect_uri)

def login_fenix_oauth(request):
    from helios_auth.views import after # if dajngo is set sync,  the import must be inside because  with the aspps are not loaded yet
    from helios_auth import url_names
    
    code = request.GET.get('code') # registration code used to obtain the access token
    payload = {'client_id': client_id, 'client_secret': clientSecret, 'redirect_uri' : redirect_uri, 'code' : code, 'grant_type': 'authorization_code'}
    response = req.post(fenixacesstokenpage, params = payload)
    
    if(response.status_code == 200):
        r_token = response.json()
        params = {'access_token': r_token['access_token']}
        #print("login_fenix_0auth() - OUATH PARAMS",params) # debug
        request.session['access_token_fenix'] =r_token['access_token'] # save token
        request.session['auth_system_name']='fenixoauth'
        return HttpResponseRedirect(reverse(url_names.AUTH_AFTER))
    else:
        print("login_fenix_0auth() - OAUTH FAILED")

def get_auth_url(request, redirect_url = None):
    # the app redirects the user to the FENIX login page
    return RequestPage

def get_user_info_after_auth(request):
    token =  request.session['access_token_fenix'] # token saved in the current session 
    params = {'access_token': token}
    resp = req.get("https://fenix.tecnico.ulisboa.pt/api/fenix/v1/person", params = params)

    #print("\n\n", "get_user_info_after_auth() - FENIX RESPONSE", resp.json()["username"])
    r_info = resp.json() # user data from Fenix
    
    del request.session['access_token_fenix']
    obj =  {'type': 'fenixoauth', 'user_id' : json.dumps(r_info["username"]),'name':r_info["name"],'info':{'email': r_info["email"]}, 'token': None}
    return obj

    

#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True

FENIX_LOGIN  = 'auth@fenix@login'
#^ matches the start of the string. this urlpattern must be include at urls.py
urlpatterns = [
  url(r'^fenix/login', login_fenix_oauth, name=FENIX_LOGIN),
]
