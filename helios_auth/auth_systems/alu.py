"""Voting identity from the existing Neon Auth session, never Google OAuth here."""
import re
from django.conf import settings

STATUS_UPDATES = False
LOGIN_MESSAGE = 'Continue with ALU account'


def get_auth_url(request, redirect_url):
  path = request.session.get('auth_return_url', '')
  match = re.fullmatch(r'/helios/elections/([0-9a-f-]{36})/(view|cast_confirm|register)', path)
  if match:
    request.session['alu_return_path'] = path
    return settings.SECURE_URL_HOST + '/auth/alu/start/' + match[1] + '/'
  return settings.ALU_BRIDGE_APP_ORIGIN + '/helios'


def can_create_election(user_id, user_info):
  # Explicit Helios administrator grants are handled by HELIOS_ADMIN_ONLY.
  return False


def get_user_info_after_auth(request):
  # The generic OAuth callback cannot authenticate an ALU identity.
  return None


def do_logout(user):
  return None


def send_message(user_id, name, user_info, subject, body):
  # Demo notification backend intentionally does not send email.
  return None
