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
from django.db.models import Q
from django.utils.safestring import mark_safe

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

  election_type = 'ecounting'

  institution = forms.CharField(max_length=100, label=_('Institution'),
                               help_text=_('Election institution'))

  name = forms.CharField( max_length=50,label=_('Election name'),
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
                                               required=False,
                                          widget=JqSplitDateTimeWidget(
                                            attrs={'date_class':'datepicker','time_class':'timepicker'}),
                                          help_text = _('Voting extension date'))

  trustees = forms.CharField(label=_('Trustees'), widget=forms.Textarea,
                             required=True,
        help_text=_('Trustees list. e.g. <br/><br/> Giannhs Gianopoulos, '
                    'giannhs@email.com<br /> Kwstas Kwstopoulos, kwstas@email.com<br />'))
  departments = forms.CharField(label=_('Schools and Departments'),
                                widget=forms.Textarea,
        help_text=_('University Schools. e.g. <br/><br/> School of Engineering <br /> School of Medicine<br />School of Informatics<br />'))

  eligibles_count = forms.ChoiceField(label=_('Eligibles count'),
                                      help_text=_('Set the eligibles count of the election'),
                                      choices = [('6','6'),('8','8')],
                                      initial='6',
                                      widget=forms.RadioSelect)
  has_department_limit = forms.BooleanField(label=_('Has department limit'), required=False, initial=True,
                                            help_text=_('4009/2011 (A\' 195)'))

  help_email = forms.EmailField(label=_('Help email'), help_text=_('Voters can contact this email for election suport'))
  help_phone = forms.CharField(label=_('Help phone'), help_text=_('Voters can contact this phone for election suport'))

  remote_mix = forms.BooleanField(label=_('Remote mix'),
                                  help_text=_('Whether or not to'
                                              ' allow remote'
                                              ' mixing.'),
                                 initial=False,
                                 required=False)


  def __init__(self, election=None, institution=None, *args, **kwargs):
    self.election = election
    self.institution = institution
    super(ElectionForm, self).__init__(*args, **kwargs)

    self.fields['institution'].widget.attrs['readonly'] = True
    self.fields['institution'].initial = institution.name

    if self.election and self.election.pk and self.election.trustee_set.count() == 1:
      self.fields['trustees'].required = False

    if self.election and self.election.frozen_at:
      self.fields['voting_starts_at'].widget.attrs['readonly'] = True
      self.fields['voting_ends_at'].widget.attrs['readonly'] = True
      self.fields['name'].widget.attrs['readonly'] = True
      self.fields['trustees'].widget.attrs['readonly'] = True
      if 'departments' in self.fields:
          self.fields['departments'].widget.attrs['readonly'] = True
    else:
      del self.fields['voting_extended_until']

  def clean(self, *args, **kwargs):
      cleaned_data = super(ElectionForm, self).clean(*args, **kwargs)

      if 'name' in cleaned_data:
          slug = slughifi(cleaned_data['name'])

      dfrom = cleaned_data['voting_starts_at']
      dto = cleaned_data['voting_ends_at']

      dextend = None
      if 'voting_extended_until' in cleaned_data:
          dextend = cleaned_data['voting_extended_until']

      if dfrom >= dto:
          raise forms.ValidationError(_("Invalid voting dates"))

      if dextend and cleaned_data['voting_extended_until'] < dto:
          raise forms.ValidationError(_("Invalid voting extension date"))

      if not 'departments' in cleaned_data:
        cleaned_data['departments'] = ''

      return cleaned_data

  def clean_trustees(self):
    trustees_list = []
    try:
      trustees = self.cleaned_data['trustees'].strip()
      trustees = trustees.split("\n")
      trustees_list = [[f.strip() for f in t.split(",")] for t in trustees if t.strip()]
    except:
      raise forms.ValidationError(_("Invalid trustess"))

    try:
      validations = [validate_email(t[1].strip()) for t in trustees_list]
    except Exception, e:
      raise forms.ValidationError(_("Invalid trustess"))

    return "\n".join(["%s,%s" % (t[0], t[1]) for t in trustees_list])

  def save(self, election, institution, params):
    is_new = not bool(election.pk)
    institution = self.institution

    data = self.cleaned_data
    data['slug'] = slughifi(data['name'])

    e = election
    e.election_type = self.election_type
    if is_new or not election.frozen_at:
      e.name = data.get('name')
      e.use_voter_aliases = True
      e.workflow_type = 'mixnet'
      e.private_p = True
      e.institution = institution
      e.help_phone = data['help_phone']
      e.help_email = data['help_email']
      e.departments = [d.strip() for d in data['departments'].strip().split("\n")]

      if e.candidates:
        new_cands = []
        for cand in e.candidates:
          if cand['department'] in e.departments:
            new_cands.append(cand)

        #if len(new_cands) != len(e.candidates):
          #messages.warning(_("Election candidates changed due to election"
                             #" institution department changes"))
        e.candidates = new_cands
        e.update_answers()


      if not e.uuid:
        e.uuid = str(uuid.uuid1())

      if is_new or not election.frozen_at:
        e.cast_url = settings.SECURE_URL_HOST + \
            reverse('helios.views.one_election_cast', args=[e.uuid])

      e.short_name = data['slug']
      count = 0

      q = Q(short_name=e.short_name)
      if e.pk:
          q = ~Q(pk=self.election.pk) & Q(short_name=e.short_name)

      short_name = e.short_name
      while Election.objects.filter(q).count() > 0:
            count += 1
            e.short_name = short_name + "-" + str(count)
            q = Q(short_name=e.short_name)
            if e.pk:
                q = ~Q(pk=self.election.pk) & Q(short_name=e.short_name)

      e.description = data['description']
      e.voting_starts_at = data['voting_starts_at']
      e.voting_ends_at = data['voting_ends_at']


    if 'voting_extended_until' in data:
      e.voting_extended_until = data['voting_extended_until']

    if is_new or not e.voting_ended_at:
      if data['remote_mix']:
        e.generate_mix_key()
      else:
        e.mix_key = ''

    if 'eligibles_count' in data:
      e.eligibles_count = data['eligibles_count']
    if 'has_department_limit' in data:
      e.has_department_limit = data['has_department_limit']

    e.save()

    if is_new:
      e.generate_helios_mixnet({"name":"zeus mixnet %d" % 1})

    if not e.get_helios_trustee():
      e.generate_trustee()

    if is_new or not election.frozen_at:
      trustees = []
      if data['trustees']:
        trustees = [t.split(",") for t in data['trustees'].split("\n")]

      for t in trustees:
        name, email = t[0], t[1]
        trustee, created = Trustee.objects.get_or_create(election=e,
                                   email=email)
        trustee.name = name
        if created:
          trustee.uuid = str(uuid.uuid1())

        trustee.save()

        if created:
            trustee.send_url_via_mail()

    return e


class ReferendumForm(ElectionForm):

      election_type = 'election'

      def __init__(self, *args, **kwargs):
          super(ReferendumForm, self).__init__(*args, **kwargs)
          del self.fields['has_department_limit']
          del self.fields['eligibles_count']
          del self.fields['departments']
          self.fields['name'].help_text = _('Election title (e.g. Memorandum'
                                            ' referendum)')


def election_form_cls(user, force_type=None):
    from zeus.forms import ElectionForm, ReferendumForm
    if user.ecounting_account:
        if force_type:
          pass
        return ElectionForm
    return ReferendumForm


class AnswerWidget(forms.TextInput):

  def render(self, *args, **kwargs):
    html = super(AnswerWidget, self).render(*args, **kwargs)
    html = u"""
    <div class="row">
    <div class="columns eleven">
    %s
    </div>
    <div class="columns one">
    <a href="#" style="font-weight: bold; color:red" class="remove_answer">X</a>
    </div>
    </div>
    """ % html
    return mark_safe(html)


DEFAULT_ANSWERS_COUNT = 2
MAX_QUESTIONS_LIMIT = getattr(settings, 'MAX_QUESTIONS_LIMIT', 1)

class QuestionForm(forms.Form):
  choice_type = forms.ChoiceField(choices=(
    ('choice', _('Choice')),
    #('ranked', _('Ranked')),
  ))
  question = forms.CharField(max_length=255, required=True)
  max_answers = forms.ChoiceField()


  def __init__(self, *args, **kwargs):
    super(QuestionForm, self).__init__(*args, **kwargs)
    answers = len(filter(lambda k: k.startswith("%s-answer_" %
                                                self.prefix), self.data))
    if not answers:
      answers = len(filter(lambda k: k.startswith("answer_"), self.initial))
    if answers == 0:
      answers = DEFAULT_ANSWERS_COUNT

    for ans in range(answers):
      field_key = 'answer_%d' % ans
      self.fields[field_key] = forms.CharField(max_length=100,
                                              required=True,
                                              widget=AnswerWidget)
      self.fields[field_key].widget.attrs = {'class': 'answer_input'}

    max_choices = map(lambda x: (x,x), range(1, answers+1))
    self.fields['max_answers'].choices = max_choices
    self.fields['max_answers'].initial = answers
    if len(self.fields['choice_type'].choices) == 1:
      self.fields['choice_type'].widget = forms.HiddenInput()
      self.fields['choice_type'].initial = 'choice'

