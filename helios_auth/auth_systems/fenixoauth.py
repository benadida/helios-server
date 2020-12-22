from django.http import HttpResponseRedirect
#from helios_auth.models import AuthenticationExpired
#from helios_auth.view_utils import render_template
#from helios_auth.views import after
#from helios_auth.models import User
import requests as req
import json

from django.urls import reverse
from django.conf.urls import url

#public_ip  = req.get('https://api.ipify.org').text
public_ip = "192.168.1.90"
print("CONFIG redirect_uri: ", public_ip)

port ="8000"
userToken = None


redirect_uri = "http://"+public_ip+":"+port+"/auth/fenix/login" # this is the address of the page on this app
client_id= "1695915081466108"
clientSecret ="z7UfPrUGHgckUSJYPTMZDItXsBYsla+NaWEI2d7+rIo6c/nv0ExAUvE/vkYf77uF64Xk1teGJvMkAu+syIz3Dg=="

print("SETUP redirect_uri:", redirect_uri)

fenixLoginpage= "https://fenix.tecnico.ulisboa.pt/oauth/userdialog?client_id=%s&redirect_uri=%s"
fenixacesstokenpage = 'https://fenix.tecnico.ulisboa.pt/oauth/access_token'
RequestPage = fenixLoginpage % (client_id, redirect_uri)


def login_fenix_oauth(request):   
    from helios_auth.views import after #if dajngo is set sync,  the import must be inside because
    # with the aspps are not loaded yet
    from helios_auth import url_names
    #try:
    #code = request.args['code']  
    code = request.GET.get('code')
    payload = {'client_id': client_id, 'client_secret': clientSecret, 'redirect_uri' : redirect_uri, 'code' : code, 'grant_type': 'authorization_code'}
    response = req.post(fenixacesstokenpage, params = payload)
    if(response.status_code == 200):
        r_token = response.json()
        params = {'access_token': r_token['access_token']}
        print("PARAMS",params) 
        #global userToken
        userToken = r_token['access_token']
        request.session['access_token_fenix'] =r_token['access_token']
        request.session['auth_system_name']='fenixoauth'    
        return HttpResponseRedirect(reverse(url_names.AUTH_AFTER))

    #except:
    #    return HttpResponseRedirect(RequestPage)


def get_auth_url(request, redirect_url = None):
    # the app redirects the user to the FENIX login page
    return RequestPage

def get_user_info_after_auth(request):
    token =  request.session['access_token_fenix'] 
    params = {'access_token': token}
    resp = req.get("https://fenix.tecnico.ulisboa.pt/api/fenix/v1/person", params = params)

    print("\n\n", "FENIX RESPONSE", resp.json()["username"])
    r_info = resp.json()
    
    del request.session['access_token_fenix']
    obj =  {'type': 'fenixoauth', 'user_id' : json.dumps(r_info["username"]),'name':r_info["name"],'info':{'email': r_info["email"]}, 'token': None}
    return obj

    

#
# Election Creation
#

def can_create_election(user_id, user_info):
  return True

FENIX_LOGIN  = 'auth@fenix@login'
#^ matches the start of the string.
urlpatterns = [
  url(r'^fenix/login', login_fenix_oauth, name=FENIX_LOGIN),
]
