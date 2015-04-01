import json

from collections import OrderedDict

from django.db.models import Q
from django.template import Context, Template, loader, RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


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

    context = RequestContext(request, vars_with_user)
    return render_to_response('server_ui/templates/%s.html' % template_name,
                              context)


def render_json(obj):
    return HttpResponse(json.dumps(obj), "application/json")


def sanitize_mobile_number(num):
    size = len(num)
    if size == 12:
        return num
    if size == 10:
        return "30%s" % str(num)
    if size > 12:
        return num[-12:]
    raise Exception("Invalid number")


def decalize(string, sep='-', chunk=2):
    if not isinstance(string, str):
        m = "argument must be an 'str', not %r" % type(string)
        raise ValueError(m)
    slist = []
    s = ''
    i = 0
    for z, c in enumerate(string):
        o = ord(c)
        if o < 32 or o > 127:
            m = ("index %d: Can only decalize printable ASCII characters "
                 "in range 32-127, not character %d(\\x%x)")
            m = m % (z, o, o)
            raise ValueError(m)
        s += "%02d" % (ord(c) - 32)
        i += 1
        if i == chunk:
            slist.append(s)
            s = ''
            i = 0

    if s:
        slist.append(s)

    return sep.join(slist)


def undecalize(string):
    i = 2
    s = ''
    d = 0
    for z, c in enumerate(string):
        if not c.isdigit():
            continue
        i -= 1
        d *= 10
        d += int(c, 10)
        if not i:
            d += 32
            if d > 127:
                m = "index %d: invalid ASCII code %d > 127" % (z, d)
                raise ValueError(m)
            s += chr(d)
            d = 0
            i = 2

    if i != 2:
        m = "Input has an odd number of decimal digits: %d" % (z + 1)
        raise ValueError(m)

    return s


def test_decalize():
    import random
    alphabet = 'abcdefghkmnpqrstuvwxyzABCDEFGHKLMNPQRSTUVWXYZ23456789'

    N = 1000
    for i in xrange(N):
        s = ''
        for j in xrange(12):
            s += random.choice(alphabet)
        dec = decalize(s, sep='-', chunk=2)
        #print s, '-', dec
        undec = undecalize(dec)
        if undec != s:
            m = "%s %s %s %s" % (i, s, dec, undec)
            raise AssertionError("decalize-undecalize mismatch: %s" % m)

    if decalize("") != undecalize(""):
        raise AssertionError()

    if decalize(" ") != "00":
        raise AssertionError()

    if undecalize("00") != " ":
        raise AssertionError()

    if undecalize("95") != "\x7f":
        raise AssertionError()

    decalize_tests = ["\x1f", "\x80"]
    for t in decalize_tests:
        try:
            decalize(t)
        except ValueError as e:
            pass
        else:
            raise AssertionError("Decalize(%s) failed to fail" % t)

    undecalize_tests = ["9012-3", "42019609"]
    for t in undecalize_tests:
        try:
            undecalize(t)
        except ValueError as e:
            pass
        else:
            raise AssertionError("Undecalize(%s) failed to fail" % t)


VOTER_TABLE_HEADERS = OrderedDict([
    ('voter_login_id', _('Registration ID')),
    ('voter_email', _('Email')),
    ('voter_surname', _('Surname')),
    ('voter_name', _('Given name')),
    ('voter_fathername', _('Middle name')),
    ('voter_mobile', _('Mobile phone')),
    ('voter_weight', _('Vote weight')),
    ('cast_votes__id', _('Has voted')),
    ('last_booth_invitation_send_at', _('Booth invitation sent at')),
    ('last_visit', _('Last visit')),
    ('actions', _('Actions'))
    ])

ELECTION_TABLE_HEADERS = OrderedDict([
    ('name', _('Name')),
    ('institution', _('Institution')),
    ('admins', _('Administrator')),
    ('created_at', _('Creation')),
    ('voting_starts_at', _('Start')),
    ('voting_ends_at', _('End')),
    ('status_display', _('Election status')),
    ('trial', _('Trial'))
    ])


VOTER_SEARCH_FIELDS = ['voter_name', 'voter_surname', 'voter_email']
VOTER_EXTRA_HEADERS = ['excluded_at']
VOTER_BOOL_KEYS_MAP = {
        'voted': ('cast_votes__id', 'nullcheck'),
        'invited': ('last_booth_invitation_send_at', 'nullcheck'),
        'excluded': ('excluded_at', 'nullcheck'),
     }

ELECTION_SEARCH_FIELDS = ['name', 'institution__name', 'admins__user_id',]
ELECTION_EXTRA_HEADERS = []
ELECTION_BOOL_KEYS_MAP = {'trial': 'trial'}



def parse_q_param(q):
    args = []
    for special_arg in q.split(" "):
        if special_arg.startswith("+") or special_arg.startswith("-"):
            q = q.replace(" " + special_arg, "")
            q = q.replace(special_arg, "")
            args.append(special_arg)
    return q, args

def get_filters(q_param, table_headers, search_fields, bool_keys_map, extra_headers=[]):

    q = Q()
    if q_param != '':
        q_parsed, extra_filters = parse_q_param(q_param)
        for search_field in search_fields:
            kwargs = {'%s__icontains' % search_field: q_parsed.strip()}
            q = q | Q(**kwargs)
        for arg in extra_filters:
            arg_type = False if arg[0] == "-" else True
            key = bool_keys_map.get(arg[1:], arg[1:])
            nullcheck = False
            if type(key) == tuple:
                nullcheck = key[1] == 'nullcheck'
                key = key[0]
            if key in (table_headers.keys() + extra_headers):
                flt = ''
                if nullcheck:
                    flt = '__isnull'
                    arg_type = not arg_type
                q = q & Q(**{'%s%s' % (key, flt): arg_type})
    return q

def get_voters_filters_with_constraints(q_param=None, constraints_include=None,
                                        constraints_exclude=None):
    q = Q()
    if q_param:
        q = q & get_filters(q_param, VOTER_TABLE_HEADERS, VOTER_SEARCH_FIELDS,
                            VOTER_BOOL_KEYS_MAP, VOTER_EXTRA_HEADERS)
    if constraints_include:
        q = q & Q(**constraints_include)
    if constraints_exclude:
        q =  q & ~Q(**constraints_exclude)
    return q
