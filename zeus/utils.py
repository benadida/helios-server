import json

from django.template import Context, Template, loader
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.conf import settings

from zeus import auth


def election_trustees_to_text(election):
    content = ""
    for trustee in election.trustees.filter(secret_key__isnull=True):
        content += "%s, %s\n" % (trustee.name, trustee.email)
    return content


def election_reverse(election, view, **extra):
    kwargs = {'election_uuid': election.uuid}
    kwargs.update(extra)
    return reverse('election_%s' % view, kwargs=kwargs)


def poll_reverse(poll, view, **extra):
    kwargs = {'election_uuid': poll.election.uuid, 'poll_uuid': poll.uuid}
    kwargs.update(extra)
    return reverse('election_poll_%s' % view, kwargs=kwargs)


def extract_trustees(content):
    trustees = []
    rows = map(lambda x:x.strip(), content.strip().split("\n"))
    for trustee in rows:
        if not trustee:
            continue
        trustee = map(lambda x:x.strip(), trustee.split(","))
        trustees.append(trustee)
    return trustees


def render_template(request, template_name, vars = {}):
    t = loader.get_template(template_name + '.html')

    vars_with_user = vars.copy()
    vars_with_user['user'] = request.zeususer
    vars_with_user['settings'] = settings
    vars_with_user['CURRENT_URL'] = request.path

    # csrf protection
    if request.session.has_key('csrf_token'):
        vars_with_user['csrf_token'] = request.session['csrf_token']

    return render_to_response('server_ui/templates/%s.html' % template_name,
                              vars_with_user)


def render_json(obj):
  return HttpResponse(json.dumps(obj), "application/json")
