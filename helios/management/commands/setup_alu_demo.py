"""Explicit operator bootstrap; bridge login never grants administration."""
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from helios.models import Election
from helios.views import ELGAMAL_PARAMS
from helios_auth.bridge_protocol import eligible_identity
from helios_auth.models import User


class Command(BaseCommand):
  help = 'Create one draft TEST election for an explicitly authorized Neon organizer.'

  def add_arguments(self, parser):
    parser.add_argument('--election-id', required=True)
    parser.add_argument('--admin-subject', required=True)
    parser.add_argument('--admin-email', required=True)

  def handle(self, *args, **options):
    try:
      election_id = str(uuid.UUID(options['election_id']))
      subject = str(uuid.UUID(options['admin_subject']))
    except ValueError as exc:
      raise CommandError('Use actual UUIDs for the election and managed Neon user.') from exc
    email = options['admin_email'].lower()
    if (election_id not in settings.ALU_BRIDGE_ELECTIONS or not eligible_identity({
        'subject': subject, 'email': email, 'email_verified': True})):
      raise CommandError('Enable this election and use the authorized organizer student address.')
    # This deliberate operator action is not a browser-supplied identity and
    # grants only this election. Subsequent login requires a fresh verified Neon
    # session with exactly this stable subject; no global admin_p is set.
    with transaction.atomic():
      if Election.get_by_uuid(election_id):
        raise CommandError('Election already exists; no permissions or ballots changed.')
      organizer, _ = User.objects.get_or_create(user_type='alu', user_id=subject,
        defaults={'name': 'TEST organizer', 'info': {'email': email, 'email_verified': True}})
      election, _ = Election.get_or_create(uuid=election_id,
        short_name='alu-test-' + election_id[:8], name='ALU TEST shared-login election',
        description='Small testing demo. Do not use for a real election.', admin=organizer)
      election.openreg = True
      election.eligibility = [{'auth_system': 'alu'}]
      election.questions = [{'answer_urls': [None, None], 'answers': ['Alice', 'Bob'],
        'choice_type': 'approval', 'max': 1, 'min': 0, 'question': 'TEST President?',
        'result_type': 'absolute', 'short_name': 'President', 'tally_type': 'homomorphic'}]
      election.generate_trustee(ELGAMAL_PARAMS)
      election.save()
    self.stdout.write('Draft TEST election ready. Verify configuration before freezing.')
