'''
Python Oauth client for Twitter

Used the SampleClient from the OAUTH.org example python client as basis.

props to leahculver for making a very hard to use but in the end usable oauth lib.

'''
import httplib
import urllib, urllib2
import time
import webbrowser
import oauth as oauth
from urlparse import urlparse

class TwitterOAuthClient(oauth.OAuthClient):
    api_root_url = 'https://twitter.com' #for testing 'http://term.ie'
    api_root_port = "80"

    #set api urls
    def request_token_url(self):
        return self.api_root_url + '/oauth/request_token'
    def authorize_url(self):
        return self.api_root_url + '/oauth/authorize'
    def authenticate_url(self):
      return self.api_root_url + '/oauth/authenticate'
    def access_token_url(self):
        return self.api_root_url + '/oauth/access_token'

    #oauth object
    def __init__(self, consumer_key, consumer_secret, oauth_token=None, oauth_token_secret=None):
        self.sha1_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        if ((oauth_token != None) and (oauth_token_secret!=None)):
            self.token = oauth.OAuthConsumer(oauth_token, oauth_token_secret)
        else:
            self.token = None

    def oauth_request(self,url, args = {}, method=None):
        if (method==None):
            if args=={}:
                method = "GET"
            else:
                method = "POST"
        req = oauth.OAuthRequest.from_consumer_and_token(self.consumer, self.token, method, url, args)
        req.sign_request(self.sha1_method, self.consumer,self.token)
        if (method=="GET"):
            return self.http_wrapper(req.to_url())
        elif (method == "POST"):
            return self.http_wrapper(req.get_normalized_http_url(),req.to_postdata())

    #this is barely working. (i think. mostly it is that everyone else is using httplib) 
    def http_wrapper(self, url, postdata={}): 
        try:
            if (postdata != {}): 
                f = urllib.urlopen(url, postdata) 
            else: 
                f = urllib.urlopen(url) 
            response = f.read()
        except:
            import traceback
            import logging, sys
            cla, exc, tb = sys.exc_info()
            logging.error(url)
            if postdata:
              logging.error("with post data")
            else:
              logging.error("without post data")
            logging.error(exc.args)
            logging.error(traceback.format_tb(tb))
            response = ""
        return response 
    

    def get_request_token(self):
        response = self.oauth_request(self.request_token_url())
        token = self.oauth_parse_response(response)
        try:
            self.token = oauth.OAuthConsumer(token['oauth_token'],token['oauth_token_secret'])
            return token
        except:
            raise oauth.OAuthError('Invalid oauth_token')

    def oauth_parse_response(self, response_string):
        r = {}
        for param in response_string.split("&"):
            pair = param.split("=")
            if (len(pair)!=2):
                break
                
            r[pair[0]]=pair[1]
        return r

    def get_authorize_url(self, token):
        return self.authorize_url() + '?oauth_token=' +token

    def get_authenticate_url(self, token):
        return self.authenticate_url() + '?oauth_token=' +token

    def get_access_token(self,token=None):
        r = self.oauth_request(self.access_token_url())
        token = self.oauth_parse_response(r)
        self.token = oauth.OAuthConsumer(token['oauth_token'],token['oauth_token_secret'])
        return token

    def oauth_request(self, url, args={}, method=None):
        if (method==None):
            if args=={}:
                method = "GET"
            else:
                method = "POST"
        req = oauth.OAuthRequest.from_consumer_and_token(self.consumer, self.token, method, url, args)
        req.sign_request(self.sha1_method, self.consumer,self.token)
        if (method=="GET"):
            return self.http_wrapper(req.to_url())
        elif (method == "POST"):
            return self.http_wrapper(req.get_normalized_http_url(),req.to_postdata())

        

if __name__ == '__main__':
    consumer_key = ''
    consumer_secret = ''
    while not consumer_key:
        consumer_key = raw_input('Please enter consumer key: ')
    while not consumer_secret:
        consumer_secret = raw_input('Please enter consumer secret: ')
    auth_client = TwitterOAuthClient(consumer_key,consumer_secret)
    tok = auth_client.get_request_token()
    token = tok['oauth_token']
    token_secret = tok['oauth_token_secret']
    url = auth_client.get_authorize_url(token) 
    webbrowser.open(url)
    print "Visit this URL to authorize your app: " + url
    response_token = raw_input('What is the oauth_token from twitter: ')
    response_client = TwitterOAuthClient(consumer_key, consumer_secret,token, token_secret) 
    tok = response_client.get_access_token()
    print "Making signed request"
    #verify user access
    content = response_client.oauth_request('https://twitter.com/account/verify_credentials.json', method='POST')
    #make an update
    #content = response_client.oauth_request('https://twitter.com/statuses/update.xml', {'status':'Updated from a python oauth client. awesome.'}, method='POST')
    print content
   
    print 'Done.'


