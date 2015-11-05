import logging

from collections import defaultdict
from time import time
from random import randint

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import email_re
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.conf import settings
from django.views.i18n import set_language

from helios.view_utils import render_template
from heliosauth.auth_systems.password import make_password
from helios.models import User, Election
from zeus.models import Institution

logger = logging.getLogger(__name__)


def setlang(request):
    lang = request.REQUEST.get('language')
    if not lang in map(lambda x:x[0], settings.LANGUAGES):
        return HttpResponseRedirect(reverse('home'))
    return set_language(request)


def home(request):
    user = request.zeususer
    bad_login = request.GET.get('bad_login')
    return render_template(request, "zeus/home", {
        'menu_active': 'home',
        'user': user,
        'bad_login': bad_login
    })


def faqs_trustee(request):
    user = request.zeususer
    return render_template(request, "zeus/faqs_admin", {
        'menu_active': 'faqs',
        'submenu': 'admin',
        'user': user
    })


def faqs_voter(request):
    user = request.zeususer
    return render_template(request, "zeus/faqs_voter", {
      'menu_active': 'faqs',
      'submenu': 'voter',
      'user': user
    })


def resources(request):
    user = request.zeususer
    return render_template(request, "zeus/resources", {
        'menu_active': 'resources',
        'user': user
    })


def contact(request):
    user = request.zeususer
    return render_template(request, "zeus/contact", {
        'menu_active': 'contact',
        'user': user
    })


def stats(request):
    user = request.zeususer._user
    if not request.zeususer.is_admin:
        return HttpResponseRedirect(reverse('home'))
    uuid = request.GET.get('uuid', None)
    election = None

    elections = Election.objects.filter()
    if not (user and user.superadmin_p):
        elections = Election.objects.filter(canceled_at__isnull=True, 
                                            completed_at__isnull=False, 
                                            voting_ended_at__isnull=False,
                                            admins__in=[user],
                                            trial=False)

    elections = elections.order_by('-created_at')

    if uuid:
        try:
            election = elections.get(uuid=uuid)
        except Election.DoesNotExist:
            return HttpResponseRedirect(reverse('home'))

    return render_template(request, 'zeus/stats', {
        'menu_active': 'stats',
        'election': election,
        'uuid': uuid,
        'user': user,
        'elections': elections
    })


_demo_addresses = defaultdict(int)
_demo_emails_per_address = defaultdict(set)


def _get_demo_user(email_address):
    password = email_address

    try:
        user = User.objects.get(name=email_address)
    except User.DoesNotExist:
        pass
    else:
        if user.user_id.startswith("demo_"):
            user.info = {'name': email_address,
                         'password': make_password(password)}
            user.save()
            return user, password

    try:
        inst = Institution.objects.get(name="DEMO")
    except Institution.DoesNotExist:
        return None, ''

    tries = 10
    while tries > 0:
        user_id = "demo_%d" % randint(1000, 1000000)
        try:
            User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            break
        tries -= 1

    if tries <= 0:
        return None, ''

    newuser = User()
    newuser.user_type = "password"
    newuser.admin_p = True
    newuser.info = {'name': email_address,
                    'password': make_password(password)}
    newuser.name = email_address
    newuser.user_id = user_id
    newuser.superadmin_p = False
    newuser.institution = inst
    newuser.ecounting_account = False
    newuser.save()
    return newuser, password


@csrf_exempt
def demo(request):
    user = request.zeususer
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    email_address = request.POST.get('email', '')

    if not email_re.match(email_address):
        msg = _("Invalid email address")
        messages.error(request, msg)
        return HttpResponseRedirect(reverse('home'))

    remote_addr = request.META.get("REMOTE_ADDR", None)
    client_address = request.META.get('HTTP_X_FORWARDED_FOR', remote_addr)
    if not client_address:
        msg = _("Client address unavailable")
        messages.error(request, msg)
        return HttpResponseRedirect(reverse('home'))

    now_seconds = int(time())
    last_seconds = _demo_addresses[client_address]
    if now_seconds - last_seconds < settings.DEMO_SUBMIT_INTERVAL_SECONDS:
        msg = _("There are too many requests from your address")
        messages.error(request, msg)
        return HttpResponseRedirect(reverse('home'))

    emails = _demo_emails_per_address[client_address]
    if email_address not in emails and len(emails) >= settings.DEMO_EMAILS_PER_IP:
        msg = _("There are too many emails registered from your address")
        messages.error(request, msg)
        return HttpResponseRedirect(reverse('home'))

    demo_user, password = _get_demo_user(email_address)
    if demo_user is None:
        msg = _("Cannot create demo users right now. Sorry.")
        messages.error(request, msg)
        return HttpResponseRedirect(reverse('home'))

    emails.add(email_address)
    mail_subject = render_to_string('email/demo_email_subject.txt',
                                    {'settings': settings}).strip()
    mail_body = render_to_string('email/demo_email_body.txt',
                                 {'settings': settings,
                                  'username': demo_user.user_id,
                                  'password': password})
    mail_from = _(settings.DEFAULT_FROM_NAME)
    mail_from += ' <%s>' % settings.DEFAULT_FROM_EMAIL
    _demo_addresses[client_address] = now_seconds

    msg = _("An email with demo credentials has been sent to %s") % email_address
    messages.success(request, msg)
    logger.info("DEMO::%s::%s::%s" % (
                email_address, client_address, demo_user.user_id))
    send_mail(mail_subject, mail_body, mail_from, [email_address])
    return HttpResponseRedirect(reverse('home'))


def error(request, code=None, message=None, type='error'):
    user = request.zeususer
    messages_len = len(messages.get_messages(request))
    if not messages_len and not message:
        return HttpResponseRedirect(reverse('home'))

    response = render_template(request, "zeus/error", {
        'code': code,
        'error_message': message,
        'error_type': type,
        'user': user,
    })
    response.status_code = int(code)
    return response



def handler403(request):
    msg = _("You do not have permission to access this page.")
    return error(request, 403, msg)


def handler500(request):
    msg = _("An error has been occured. Please notify the server admin.")
    return error(request, 500, msg)


def handler400(request):
    msg = _("An error has been occured. Please notify the server admin.")
    return error(request, 400, msg)


def handler404(request):
    msg = _("The requested page was not found.")
    return error(request, 404 , msg)
