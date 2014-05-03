from django.conf.urls.defaults import *

from django.conf import settings

from views import *

urlpatterns = None
urlpatterns = patterns('',
  #(r'^$', index),
  #(r'^publickeygenerator$', public_key_form),

  #(r'^communication_keys/view/$', keys_home),
  #(r'^communication_keys/download$', keys_download),

  #(r'^communication_keys/view/(?P<key_id>[^/]+)/public_key_encrypt/$', show_key_encrypt),
  #(r'^communication_keys/view/(?P<key_id>[^/]+)/public_key_signing/$', show_key_signing),
  #(r'^communication_keys/view/(?P<key_id>[^/]+)/pok_encrypt/$', show_pok_encrypt),
  #(r'^communication_keys/view/(?P<key_id>[^/]+)/pok_signing/$', show_pok_signing),
  #(r'^elections/$', show_elections),
  #(r'^elections/(?P<election_id>[^/]+)/$', election_index),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/$', election_trustees_home),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/add/$', election_trustees_add),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/add/(?P<key_id>[^/]+)/$', election_trustees_add_from_id),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/remove/$', election_trustees_remove),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/remove/(?P<trustee_id>[^/]+)/$', election_trustees_remove_from_id),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/freeze_trustees_list/$', freeze_trustees_list),

  #(r'^elections/(?P<election_id>[^/]+)/trustees/view/(?P<key_id>[^/]+)/public_key_encrypt/$', election_show_key_encrypt),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/view/(?P<key_id>[^/]+)/public_key_signing/$', election_show_key_signing),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/view/(?P<key_id>[^/]+)/pok_encrypt/$', election_show_pok_encrypt),
  #(r'^elections/(?P<election_id>[^/]+)/trustees/view/(?P<key_id>[^/]+)/pok_signing/$', election_show_pok_signing),


  #(r'^elections/(?P<election_id>[^/]+)/encrypted_shares/view/$', encrypted_shares_home),
  #(r'^elections/(?P<election_id>[^/]+)/encrypted_shares/view/(?P<share_id>[^/]+)/$', show_encrypted_share),
  #(r'^elections/(?P<election_id>[^/]+)/encrypted_shares/view/all/(?P<receiver_id>[^/]+)/$', show_all),

  (r'^elections/(?P<election_id>[^/]+)/download/$', download_index),
  (r'^elections/(?P<election_id>[^/]+)/download/(?P<receiver_id>[^/]+)/$', download_data),

  #(r'^elections/(?P<election_id>[^/]+)/decrypt/(?P<receiver_id>[^/]+)/$', decrypt_shares),

  #(r'^communication_keys/add/', add),
)
