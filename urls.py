# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings

def quick_start_election(request):
  from zeus.models import *
  from helios.models import *
  from heliosauth.models import *
  from heliosauth.auth_systems.password import create_user
  from django.http import *

  eid = request.GET.get("elid", "test")

  clear = False
  if eid != "test":
    clear = True

  if clear:
    Faculty.objects.filter(name="Panepistimio %s name" % eid).delete()

  fac = Faculty.objects.create(name="Panepistimio %s name" % eid)

  commision = []
  voters = []

  for i in range(1,3):
    commid = commail = "xrhsths_eforeutikhs_%s_%d@dispostable.com" % (eid, i)
    commname = "Melos eforeytikhs epitrohs %s %d" % (eid, i)
    if clear:
      try:
        User.objects.filter(user_id=commid).delete()
      except:
        pass

    commision.append(commid)
    user = create_user(commid, "1234", commname)
    user.faculty = fac
    user.admin_p = True
    user.save()

  voter_data = ""
  for i in range(1, 20):
    voter_data += "voter%d@dispostable.com,voter%d@dispostable.com,Psifoforos %d" % (i,i,i)
    voter_data += "\n"

  resp = "<html><h1>Xrhstes eforeytikhs</h1><ul>"
  for comm in commision:
    resp += "<li>%s (pass:1234)</li>" % comm

  resp += "</ul><h2>Voters cvs</h2><pre>%s</pre></html>" % voter_data


  return HttpResponse(resp)


urlpatterns = patterns(
    '',
    (r'^auth/', include('heliosauth.urls')),
    (r'^helios/test-create', quick_start_election),
    (r'^helios/', include('helios.urls')),

    # SHOULD BE REPLACED BY APACHE STATIC PATH
    (r'booth/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.BOOTH_STATIC_PATH}),
    (r'verifier/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.VERIFIER_STATIC_PATH}),

    (r'static/auth/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/auth/media'}),
    (r'static/helios/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/helios/media'}),
    (r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/server_ui/media'}),

    (r'^', include('server_ui.urls')),

    )
