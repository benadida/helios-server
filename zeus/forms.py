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

def initial_voting_starts_at():
    return datetime.now()

def initial_voting_ends_at():
    return datetime.now() + timedelta(hours=12)

class ElectionForm(forms.Form):
  institution = forms.CharField(max_length=100, label=_('Institution'),
                               help_text=_('Election institution'))

  name = forms.CharField( max_length=100,label=_('Election name'),
                         widget=forms.TextInput(attrs={'size':60}),
                         initial="",
                         help_text=_('the name of the election (e.g. University of Piraeus 2014 elections).'))
  description = forms.CharField(widget=forms.Textarea,
                  initial="",
                  label=_('Description'),
                 help_text=_('Election description'))
  voting_starts_at = JqSplitDateTimeField(label=_('Voting starts at'),
                                          initial=initial_voting_starts_at,
                                          widget=JqSplitDateTimeWidget(
                                            attrs={'date_class':'datepicker','time_class':'timepicker'}),
                                          help_text = _('When voting starts'))
  voting_ends_at = JqSplitDateTimeField(label=_('Voting ends at'),
                                        initial=initial_voting_ends_at,
                                          widget=JqSplitDateTimeWidget(
                                            attrs={'date_class':'datepicker','time_class':'timepicker'}),
                                          help_text = _('When voting ends'))

  #create_test_voters = forms.BooleanField(required=False)
  voting_extended_until = JqSplitDateTimeField(label=_('Voting extended until'),
                                          initial=datetime.now,
                                          widget=JqSplitDateTimeWidget(
                                            attrs={'date_class':'datepicker','time_class':'timepicker'}),
                                          help_text = _('Voting extension date'))

  trustees = forms.CharField(label=_('Trustees'), widget=forms.Textarea,
        help_text=_('Trustees list. e.g. <br/><br/> Giannhs Gianopoulos, '
                    'giannhs@email.com<br /> Kwstas Kwstopoulos, kwstas@email.com<br />'))
  departments = forms.CharField(label=_('Schools and Departments'),
                                widget=forms.Textarea,
        help_text=_('University Schools. e.g. <br/><br/> School of Engineering <br /> School of Medicine<br />School of Informatics<br />'))

  eligibles_count = forms.IntegerField(label=_('Eligibles count'),
                                       help_text=_('Set the eligibles count of the election'), initial=6)
  has_department_limit = forms.BooleanField(label=_('Has department limit'), required=False, initial=True,
                                            help_text=_('4009/2011 (A\' 195)'))

  help_email = forms.EmailField(label=_('Help email'), help_text=_('Voters can contact this email for election suport'))
  help_phone = forms.CharField(label=_('Help phone'), help_text=_('Voters can contact this phone for election suport'))


  def __init__(self, election=None, institution=None, *args, **kwargs):
    self.election = election
    self.institution = institution
    super(ElectionForm, self).__init__(*args, **kwargs)

    self.fields['institution'].widget.attrs['readonly'] = True
    self.fields['institution'].initial = institution.name

    if self.election and self.election.frozen_at:
      self.fields['voting_starts_at'].widget.attrs['readonly'] = True
      self.fields['voting_ends_at'].widget.attrs['readonly'] = True
      self.fields['voting_starts_at'].widget.attrs['disabled'] = True
      self.fields['voting_ends_at'].widget.attrs['disabled'] = True
      self.fields['name'].widget.attrs['disabled'] = True
      self.fields['name'].widget.attrs['readonly'] = True
      del self.fields['trustees']
      del self.fields['departments']
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

  def save(self, election, institution, params):
    is_new = not bool(election.pk)
    institution = self.institution

    data = self.cleaned_data
    data['slug'] = slughifi(data['name'])

    e = election
    if is_new or not election.frozen_at:
      e.name = data.get('name')
      e.use_voter_aliases = True
      e.workflow_type = 'mixnet'
      e.private_p = True
      e.institution = institution
      e.help_phone = data['help_phone']
      e.help_email = data['help_email']
      e.eligibles_count = data['eligibles_count']
      e.has_department_limit = data['has_department_limit']
      e.departments = [d.strip() for d in data['departments'].split("\n")]

      if e.candidates:
        new_cands = []
        for cand in e.candidates:
          if cand['department'] in e.departments:
            new_cands.append(cand)

        if len(new_cands) != len(e.candidates):
          messages.warning(_("Election candidates changed due to election"
                             " institution department changes"))
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
      e.generate_helios_mixnet({"name":"zeus mixnet %d" % 1})

    if not e.get_helios_trustee():
      e.generate_trustee()

    if is_new or not election.frozen_at:
      existing_trustees = [] if is_new else list(e.trustee_set.all())
      trustees = [t.split(",") for t in data['trustees'].split("\n")]

      for t in trustees:
        name, email = t[0], t[1]
        trustee, created = Trustee.objects.get_or_create(election=e,
                                   email=email)
        trustee.name = name
        if created:
          trustee.uuid = str(uuid.uuid1())

        else:
            self.fields.pop('voting_extended_until', None)

        trustee.save()

        if created:
            trustee.send_url_via_mail()

    return e
