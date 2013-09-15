# -*- coding: utf-8 -*-
"""
Forms for Zeus
"""
import uuid
import copy

from datetime import datetime, timedelta

from django import forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import widgets
from django.db import transaction
from django.conf import settings
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.contrib.auth.hashers import check_password, make_password
from django.forms.models import BaseModelFormSet

from helios.models import Election, Poll, Trustee, Voter
from heliosauth.models import User

from zeus.utils import extract_trustees, election_trustees_to_text
from zeus.widgets import JqSplitDateTimeField, JqSplitDateTimeWidget
from zeus import help_texts as help

from django.core.validators import validate_email


LOG_CHANGED_FIELDS = [
    "name",
    "voting_starts_at",
    "voting_ends_at",
    "voting_extended_until",
    "description",
    "help_email",
    "help_phone"
]

def election_form_formfield_cb(f, **kwargs):
    if f.name in ['voting_starts_at', 'voting_ends_at',
                  'voting_extended_until']:
        widget = JqSplitDateTimeWidget(attrs={'date_class': 'datepicker',
                                              'time_class': 'timepicker'})
        return JqSplitDateTimeField(label=f.verbose_name,
                                    initial=f.default,
                                    widget=widget,
                                    required=not f.blank,
                                    help_text=f.help_text)
    return f.formfield()


class ElectionForm(forms.ModelForm):

    formfield_callback = election_form_formfield_cb
    trustees = forms.CharField(label=_('Trustees'), required=False,
                               widget=forms.Textarea,
                               help_text=help.trustees)
    remote_mixes = forms.BooleanField(label=_('Multiple mixnets'),
                                      required=False,
                                      help_text=help.remote_mixes)

    FIELD_REQUIRED_FEATURES = {
        'trustees': ['edit_trustees'],
        'name': ['edit_name'],
        'description': ['edit_description'],
        'election_module': ['edit_type'],
        'voting_starts_at': ['edit_voting_starts_at'],
        'voting_ends_at': ['edit_voting_ends_at'],
        'voting_ends_at': ['edit_voting_ends_at'],
        'voting_extended_until': ['edit_voting_extended_until'],
        'remote_mixes': ['edit_remote_mixes'],
        'trial': ['edit_trial'],
    }

    class Meta:
        model = Election
        fields = ('trial', 'election_module', 'name', 'description',
                  'voting_starts_at', 'voting_ends_at',
                  'voting_extended_until',
                  'trustees', 'help_email', 'help_phone')

    def __init__(self, institution, *args, **kwargs):
        self.institution = institution
        super(ElectionForm, self).__init__(*args, **kwargs)

        self.creating = True
        self._inital_data = {}
        if self.instance and self.instance.pk:
            self._initial_data = {}
            for field in LOG_CHANGED_FIELDS:
                self._initial_data[field] = self.initial[field]
            self.creating = False

        if self.instance and self.instance.pk:
            self.fields.get('trustees').initial = \
                election_trustees_to_text(self.instance)
            self.fields.get('remote_mixes').initial = \
                bool(self.instance.mix_key)

        for field, features in self.FIELD_REQUIRED_FEATURES.iteritems():
            editable = all([self.instance.check_feature(f) for \
                            f in features])

            widget = self.fields.get(field).widget
            if not editable:
                self.fields.get(field).widget.attrs['readonly'] = True
                if isinstance(widget, forms.CheckboxInput):
                    self.fields.get(field).widget.attrs['disabled'] = True

    def clean(self):
        data = super(ElectionForm, self).clean()
        self.clean_voting_dates(data.get('voting_starts_at'),
                                data.get('voting_ends_at'),
                                data.get('voting_extended_until'))

        for field, features in self.FIELD_REQUIRED_FEATURES.iteritems():
            if not self.instance.pk:
                continue
            editable = all([self.instance.check_feature(f) for \
                            f in features])
            if not editable and field in self.cleaned_data:
                if field == 'trustees':
                    self.cleaned_data[field] = \
                        election_trustees_to_text(self.instance)
                elif field == 'remote_mixes':
                    self.cleaned_data[field] = bool(self.instance.mix_key)
                else:
                    self.cleaned_data[field] = getattr(self.instance, field)

        return data

    def clean_voting_dates(self, starts, ends, extension):
        if ends < datetime.now() and self.instance.feature_edit_voting_ends_at:
            raise forms.ValidationError(_("Invalid voting end date"))
        if starts >= ends:
            raise forms.ValidationError(_("Invalid voting dates"))
        if extension and extension <= ends:
            raise forms.ValidationError(_("Invalid voting extension date"))

    def clean_trustees(self):
        trustees = self.cleaned_data.get('trustees')
        try:
            for tname, temail in extract_trustees(trustees):
                validate_email(temail)
        except:
            raise forms.ValidationError(_("Invalid trustees format"))
        return trustees

    def log_changed_fields(self, instance):
        for field in LOG_CHANGED_FIELDS:
            if field in self.changed_data:
                inital = self._initial_data[field]
                newvalue = self.cleaned_data[field]
                instance.logger.info("Field '%s' changed from %r to %r", field,
                                    inital, newvalue)


    def save(self, *args, **kwargs):
        remote_mixes = self.cleaned_data.get('remote_mixes')
        if remote_mixes:
            self.instance.generate_mix_key()
        else:
            self.instance.mix_key = None

        saved = super(ElectionForm, self).save(*args, **kwargs)
        trustees = extract_trustees(self.cleaned_data.get('trustees'))
        saved.institution = self.institution
        saved.save()
        if saved.feature_edit_trustees:
            saved.update_trustees(trustees)

        if self.creating:
            saved.logger.info("Election created")
        else:
            saved.logger.info("Election updated %r", self.changed_data)
            self.log_changed_fields(saved)
        return saved


class AnswerWidget(forms.TextInput):

    def render(self, *args, **kwargs):
        html = super(AnswerWidget, self).render(*args, **kwargs)
        html = u"""
        <div class="row">
        <div class="columns eleven">
        %s
        </div>
        <div class="columns one">
        <a href="#" style="font-weight: bold; color:red"
        class="remove_answer">X</a>
        </div>
        </div>
        """ % html
        return mark_safe(html)


DEFAULT_ANSWERS_COUNT = 2
MAX_QUESTIONS_LIMIT = getattr(settings, 'MAX_QUESTIONS_LIMIT', 1)


class QuestionForm(forms.Form):
    choice_type = forms.ChoiceField(choices=(
        ('choice', _('Choice')),
    ))
    question = forms.CharField(label=_("Question"), max_length=255,
                               required=True)
    min_answers = forms.ChoiceField(label=_("Min answers"))
    max_answers = forms.ChoiceField(label=_("Max answers"))

    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        answers = len(filter(lambda k: k.startswith("%s-answer_" %
                                                self.prefix), self.data))
        if not answers:
            answers = len(filter(lambda k: k.startswith("answer_"),
                                 self.initial))
        if answers == 0:
            answers = DEFAULT_ANSWERS_COUNT

        for ans in range(answers):
            field_key = 'answer_%d' % ans
            self.fields[field_key] = forms.CharField(max_length=100,
                                              required=True,
                                              widget=AnswerWidget)
            self.fields[field_key].widget.attrs = {'class': 'answer_input'}

        max_choices = map(lambda x: (x,x), range(1, answers+1))
        min_choices = map(lambda x: (x,x), range(0, answers+1))

        self.fields['max_answers'].choices = max_choices
        self.fields['max_answers'].initial = answers
        self.fields['min_answers'].choices = max_choices
        self.fields['min_answers'].initial = 0

        if len(self.fields['choice_type'].choices) == 1:
            self.fields['choice_type'].widget = forms.HiddenInput()
            self.fields['choice_type'].initial = 'choice'

    def clean(self):
        max_answers = int(self.cleaned_data.get('max_answers'))
        min_answers = int(self.cleaned_data.get('min_answers'))
        if min_answers > max_answers:
            raise forms.ValidationError(_("Max answers should be greater "
                                          "or equal to min answers"))
        return self.cleaned_data


class PartyForm(QuestionForm):
    question = forms.CharField(label=_("Party name"), max_length=255,
                               required=True)


class LoginForm(forms.Form):
    username = forms.CharField(label=_('Username'),
                               max_length=50)
    password = forms.CharField(label=_('Password'),
                               widget=forms.PasswordInput(),
                               max_length=100)

    def clean(self):
        self._user_cache = None
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        try:
            user = User.objects.get(user_id=username)
        except User.DoesNotExist:
            raise forms.ValidationError(_("Invalid username or password"))

        if check_password(password, user.info['password']):
            self._user_cache = user
            return self.cleaned_data
        else:
            raise forms.ValidationError(_("Invalid username or password"))


class PollForm(forms.ModelForm):

    class Meta:
        model = Poll
        fields = ('name', )


class PollFormSet(BaseModelFormSet):
    def save(self, election, *args, **kwargs):
        instances = super(PollFormSet, self).save(*args, commit=False,
                                                  **kwargs)
        for instance in instances:
            instance.election = election
            instance.save()

        return instances


SEND_TO_CHOICES = [
    ('all', _('all voters')),
    ('voted', _('voters who have cast a ballot')),
    ('not-voted', _('voters who have not yet cast a ballot'))
]

class EmailVotersForm(forms.Form):
    subject = forms.CharField(label=_('Email subject'), max_length=80,
                              required=False)
    body = forms.CharField(label=_('Email body'), max_length=2000,
                           widget=forms.Textarea, required=False)
    send_to = forms.ChoiceField(label=_("Send To"), initial="all",
                                choices=SEND_TO_CHOICES)


class ChangePasswordForm(forms.Form):
    password = forms.CharField(label=_('Current password'), widget=forms.PasswordInput)
    new_password = forms.CharField(label=_('New password'), widget=forms.PasswordInput)
    new_password_confirm = forms.CharField(label=_('New password confirm'), widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def save(self):
        user = self.user
        pwd = make_password(self.cleaned_data['new_password'].strip())
        user.info['password'] = pwd
        user.save()

    def clean(self):
        cl = super(ChangePasswordForm, self).clean()
        pwd = self.cleaned_data['password'].strip()
        if not check_password(pwd, self.user.info['password']):
            raise forms.ValidationError(_('Invalid password'))
        if not self.cleaned_data.get('new_password') == \
           self.cleaned_data.get('new_password_confirm'):
            raise forms.ValidationError(_('Passwords don\'t match'))
        return cl

class PollVoterLoginForm(forms.Form):

    email = forms.EmailField(label=_('Email'))
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput)

    def __init__(self, poll, *args, **kwargs):
        self.poll = poll
        self._voter = None
        super(PollVoterLoginForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(PollVoterLoginForm, self).clean()
        email = self.cleaned_data.get('email')
        secret = self.cleaned_data.get('password')
        try:
            self._voter = self.poll.voters.get(voter_email=email,
                                               voter_password=secret)
        except Voter.DoesNotExist:
            raise forms.ValidationError(_("Invalid email or password"))
        return cleaned_data
