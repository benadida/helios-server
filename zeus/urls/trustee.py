from django.conf.urls.defaults import *

urlpatterns = patterns('zeus.views.trustee',
    url(r'l/(?P<trustee_email>[^/]+)/(?P<trustee_secret>[^/]+)$',
         'login', name="election_trustee_login"),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/home$', 'home'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/sendurl$', 'send_url'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/keygenerator$', 'keygenerator'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/check-sk$', 'check_sk'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-pk$', 'upload_pk'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/decrypt-and-prove$',
        #'decrypt_and_prove'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/download-ciphers$',
        #'download_ciphers'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-decryption$',
        #'upload_decryption'),
    #url(r'^/trustees/(?P<trustee_uuid>[^/]+)/verify-key$',
        #'verify_key'),
)

election_patterns = patterns('zeus.views.trustee',
    url(r'^home$', 'home', name='election_trustee_home'),
    url(r'^keygen$', 'keygen', name='election_trustee_keygen'),
    url(r'^upload_pk$', 'upload_pk', name='election_trustee_upload_pk'),
    url(r'^check_sk$', 'check_sk', name='election_trustee_check_sk'),
    url(r'^verify_key$', 'verify_key', name='election_trustee_verify_key'),
    url(r'^json$', 'json_data', name='trustee_json_data'),
)
