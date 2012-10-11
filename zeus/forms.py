# -*- coding: utf-8 -*-
"""
Forms for Zeus
"""
import uuid

from datetime import datetime, timedelta

from django import forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import widgets
from django.db import transaction
from django.conf import settings

from helios.models import Election, Trustee
from heliosauth.models import User

from zeus.slugify import slughifi

from zeus.widgets import JqSplitDateTimeField, JqSplitDateTimeWidget

from django.core.validators import validate_email


class ElectionCandidatesForm(forms.Form):

  def __init__(self, election, *args, **kwargs):
    self.election = election
    super(ElectionCandidatesForm, self).__init__(*args, **kwargs)


  def save(self):
    self.election.save()


def _in_two_days():
    return datetime.now() + timedelta(days=2)

def _in_one_day():
    return datetime.now() + timedelta(days=1)

INITIAL_CANDIDATES = """
Onoma epwnymo 1
Onoma epwnymo 2
Onoma epwnymo 3
Onoma epwnymo 4
Onoma epwnymo 5
"""

def add_test_voters(election):
  from helios.models import Voter
  import random

  new_voters = []
  for v in range(50):
    voter_id = email = "voter_%d@dispostable.com" % (v, )
    voter_uuid = str(uuid.uuid4())
    name = "Voter %d" % v

    voter = Voter(uuid= voter_uuid, user = None, voter_login_id = voter_id,
                  voter_name = name, voter_email = email, election = election)
    voter.generate_password()
    new_voters.append(voter)
    voter.save()

  last_alias_num = 0
  num_voters = 50
  voter_alias_integers = range(last_alias_num+1, last_alias_num+1+num_voters)
  random.shuffle(voter_alias_integers)
  for i, voter in enumerate(new_voters):
    voter.alias = 'V%s' % voter_alias_integers[i]
    voter.init_audit_passwords()
    voter.save()

  return new_voters

class ElectionForm(forms.Form):
  name = forms.CharField( max_length=100,label=_('Election name'),
                         widget=forms.TextInput(attrs={'size':60}),
                         initial="",
                         help_text=_('the name of the election (e.g. University of Piraeus 2014 elections.'))
  description = forms.CharField(widget=forms.Textarea,
                  initial="",
                 help_text=_('Election description'))
  voting_starts_at = JqSplitDateTimeField(initial=datetime.now,
                                          widget=JqSplitDateTimeWidget(
                                            attrs={'date_class':'datepicker','time_class':'timepicker'}),
                                          help_text = _('When voting starts'))
  voting_ends_at = JqSplitDateTimeField(initial=datetime.now,
                                          widget=JqSplitDateTimeWidget(
                                            attrs={'date_class':'datepicker','time_class':'timepicker'}),
                                          help_text = _('When voting ends'))

  #create_test_voters = forms.BooleanField(required=False)
  voting_extended_until = JqSplitDateTimeField(initial=datetime.now,
                                          widget=JqSplitDateTimeWidget(
                                            attrs={'date_class':'datepicker','time_class':'timepicker'}),
                                          help_text = _('Voting extension date'))

  trustees = forms.CharField(widget=forms.Textarea,
        help_text=_('Trustees list. e.g. <br/><br/> Giannhs Gianopoulos, '
                    'giannhs@email.com<br /> Kwstas Kwstopoulos, kwstas@email.com<br />'))
  faculties = forms.CharField(widget=forms.Textarea,
        help_text=_('University faculties. e.g. <br/><br/> Faculty 1<br />'
                    'Faculty 2<br /> Faculty 3<br />'))

  help_email = forms.EmailField(help_text=_('Voters can contact this email for election suport'))
  help_phone = forms.CharField(help_text=_('Voters can contact this phone for election suport'))


  def __init__(self, election=None, *args, **kwargs):
    self.election = election
    super(ElectionForm, self).__init__(*args, **kwargs)

    if self.election and self.election.frozen_at:
      self.fields['voting_starts_at'].widget.attrs['readonly'] = True
      self.fields['voting_ends_at'].widget.attrs['readonly'] = True
      self.fields['voting_starts_at'].widget.attrs['disabled'] = True
      self.fields['voting_ends_at'].widget.attrs['disabled'] = True
      self.fields['name'].widget.attrs['disabled'] = True
      self.fields['name'].widget.attrs['readonly'] = True
      del self.fields['trustees']
      del self.fields['schools']

      self.fields['faculties'].initial = self.election.faculties.join("\n")
    else:
      del self.fields['voting_extended_until']

  def clean_trustees(self):
    trustees_list = []
    try:
      trustees = self.cleaned_data['trustees'].strip()
      trustees = trustees.split("\n")
      trustees_list = [[f.strip() for f in t.split(",")] for t in trustees if t.strip()]
    except:
      raise forms.ValidationError(_("Invalid trustess"))

    validations = [validate_email(t[1].strip()) for t in trustees_list]

    return "\n".join(["%s, %s" % (t[0], t[1]) for t in trustees_list])

  def save(self, election, faculty, params):
    is_new = not bool(election.pk)

    data = self.cleaned_data
    data['slug'] = slughifi(data['name'])

    e = election
    if is_new or not election.frozen_at:
      e.name = data.get('name')
      e.use_voter_aliases = True
      e.workflow_type = 'mixnet'
      e.private_p = True
      e.faculty = faculty
      e.help_phone = data['help_phone']
      e.help_email = data['help_email']
      e.faculties = [d.strip() for d in data['faculties'].split("\n")]

      if e.candidates:
        new_cands = []
        for cand in e.candidates:
          if cand['faculty'] in e.faculties:
            new_cands.append(cand)

        if len(new_cands) != len(e.candidates):
          messages.warning(_("Election candidates changed due to faculties"
                             " changes"))
        e.candidates = new_cands


      if not e.uuid:
        e.uuid = str(uuid.uuid1())

      if is_new or not election.frozen_at:
        e.cast_url = settings.SECURE_URL_HOST + \
            reverse('helios.views.one_election_cast', args=[e.uuid])

      e.short_name = data['slug']
      count = 0
      while Election.objects.filter(short_name=e.short_name).count() > 0:
        count += 1
        e.short_name = e.short_name + "-" + str(count)

      e.description = data['description']
      e.voting_starts_at = data['voting_starts_at']
      e.voting_ends_at = data['voting_ends_at']



    if 'voting_extended_until' in data:
      e.voting_extended_until = data['voting_extended_until']

    e.save()

    if is_new:
      commitee = User.objects.filter(faculty=faculty)
      e.generate_helios_mixnet({"name":"zeus mixnet %d" % 1})

    if not e.get_helios_trustee():
      e.generate_trustee(params)

    if is_new or not election.frozen_at:
      existing_trustees = [] if is_new else list(e.trustee_set.all())
      trustees = [t.split(",") for t in data['trustees'].split("\n")]

      for t in trustees:
        name, email = t[0], t[1]
        if not existing_trustees:
          trustee = Trustee(uuid=str(uuid.uuid1()), election=e,
                                   name=name,
                                   email=email)
          trustee.save()
          trustee.send_url_via_mail()

        else:
          try:
            trustee = e.trustee_set.get(email=email)
            trustee.name = name
            trustee.save()
          except:
            trustee = Trustee(uuid=str(uuid.uuid1()), election=e,
                                     name=name,
                                     email=email)
            trustee.save()
            trustee.send_url_via_mail()

      emails = [t[1] for t in trustees]
      for trustee in e.trustee_set.all():
        if trustee.email not in emails and not trustee == e.get_helios_trustee():
          print trustee.email, e.get_helios_trustee
          trustee.delete()


    # post creation
    return e, e.trustee_set.all()

