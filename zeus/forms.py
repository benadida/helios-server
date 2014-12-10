# -*- coding: utf-8 -*-
"""
Forms for Zeus
"""
import uuid
import copy
import json

from datetime import datetime, timedelta

from django import forms
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import widgets
from django.db import transaction
from django.conf import settings
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.contrib.auth.hashers import check_password, make_password
from django.forms.models import BaseModelFormSet
from django.forms.widgets import Select, MultiWidget, DateInput, TextInput
from django.forms.formsets import BaseFormSet

from helios.models import Election, Poll, Trustee, Voter
from heliosauth.models import User

from zeus.utils import extract_trustees, election_trustees_to_text
from zeus.widgets import JqSplitDateTimeField, JqSplitDateTimeWidget
from zeus import help_texts as help
from zeus.utils import undecalize

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
    linked_polls = forms.BooleanField(label=_("Linked polls (experimental)"),
                                      required=False)

    FIELD_REQUIRED_FEATURES = {
        'trustees': ['edit_trustees'],
        'name': ['edit_name'],
        'description': ['edit_description'],
        'election_module': ['edit_type'],
        'voting_starts_at': ['edit_voting_starts_at'],
        'voting_ends_at': ['edit_voting_ends_at'],
        'voting_extended_until': ['edit_voting_extended_until'],
        'remote_mixes': ['edit_remote_mixes'],
        'trial': ['edit_trial'],
        'departments': ['edit_departments'],
        'linked_polls': ['edit_linked_polls']
    }

    class Meta:
        model = Election
        fields = ('trial', 'election_module', 'name', 'description',
                  'departments', 'voting_starts_at', 'voting_ends_at',
                  'voting_extended_until',
                  'trustees', 'help_email', 'help_phone', 
                  'communication_language', 'linked_polls')

    def __init__(self, institution, *args, **kwargs):
        self.institution = institution
        if kwargs.get('lang'):
            lang = kwargs.pop('lang')
        else:
            lang = None
        super(ElectionForm, self).__init__(*args, **kwargs)
        choices = [('en', _('English')),
                   ('el', _('Greek'))]
        help_text = _("Set the language that will be used for email messages")
        self.fields['communication_language'] = forms.ChoiceField(label=
                                                    _("Communication language"),
                                                    choices=choices,
                                                    initial=lang,
                                                    help_text = help_text)
        self.creating = True
        self._inital_data = {}
        if self.instance and self.instance.pk:
            self._initial_data = {}
            for field in LOG_CHANGED_FIELDS:
                self._initial_data[field] = self.initial[field]
            self.creating = False
        if 'election_module' in self.data:
            if self.data['election_module'] != 'stv':
                self.fields['departments'].required = False
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

        if not self.instance.frozen_at:
            self.fields.pop('voting_extended_until')

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

    def clean_departments(self):
        deps = self.cleaned_data.get('departments')
        deps_arr = deps.split('\n')
        cleaned_deps = []
        for item in deps_arr:
            item = item.strip()
            item = item.lstrip()
            if item:
                cleaned_deps.append(item)
        cleaned_deps = '\n'.join(cleaned_deps)
        return cleaned_deps

    def clean_voting_dates(self, starts, ends, extension):
        if starts and ends:
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


class QuestionBaseForm(forms.Form):
    choice_type = forms.ChoiceField(choices=(
        ('choice', _('Choice')),
    ))
    question = forms.CharField(label=_("Question"), max_length=5000,
                               required=True, 
                               widget=forms.Textarea(attrs={
                                'rows': 4,
                                'class': 'textarea'
                               }))

    def __init__(self, *args, **kwargs):
        super(QuestionBaseForm, self).__init__(*args, **kwargs)
        if len(self.fields['choice_type'].choices) == 1:
            self.fields['choice_type'].widget = forms.HiddenInput()
            self.fields['choice_type'].initial = 'choice'

        answers = len(filter(lambda k: k.startswith("%s-answer_" %
                                                self.prefix), self.data))
        if not answers:
            answers = len(filter(lambda k: k.startswith("answer_") and not "indexes" in k,
                                 self.initial.keys()))

        if answers == 0:
            answers = DEFAULT_ANSWERS_COUNT

        for ans in range(answers):
            field_key = 'answer_%d' % ans
            self.fields[field_key] = forms.CharField(max_length=300,
                                              required=True,
                                              widget=AnswerWidget)
            self.fields[field_key].widget.attrs = {'class': 'answer_input'}

        self._answers = answers

    def clean_question(self):
        q = self.cleaned_data.get('question', '')
        if '%' in q:
            raise forms.ValidationError(_("&#37; is not a valid character"))
        return q.replace(": ", ":\t")


class QuestionForm(QuestionBaseForm):
    min_answers = forms.ChoiceField(label=_("Min answers"))
    max_answers = forms.ChoiceField(label=_("Max answers"))

    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        answers = self._answers
        max_choices = map(lambda x: (x,x), range(1, answers+1))
        min_choices = map(lambda x: (x,x), range(0, answers+1))

        self.fields['max_answers'].choices = max_choices
        self.fields['max_answers'].initial = self._answers
        self.fields['min_answers'].choices = max_choices
        self.fields['min_answers'].initial = 0


    def clean(self):
        max_answers = int(self.cleaned_data.get('max_answers'))
        min_answers = int(self.cleaned_data.get('min_answers'))
        if min_answers > max_answers:
            raise forms.ValidationError(_("Max answers should be greater "
                                          "or equal to min answers"))
        answer_list = []
        for key in self.cleaned_data:
            if key.startswith('answer_'):
                if '%' in self.cleaned_data[key]:
                    raise forms.ValidationError(_("&#37; is not a valid character"))
                answer_list.append(self.cleaned_data[key])
        if len(answer_list) > len(set(answer_list)):
            raise forms.ValidationError(_("No duplicate choices allowed"))
        return self.cleaned_data


class PartyForm(QuestionForm):
    question = forms.CharField(label=_("Party name"), max_length=255,
                               required=True)

SCORES_DEFAULT_LEN = 2
SCORES_CHOICES = [(x,x) for x in range(1, 10)]
class ScoresForm(QuestionBaseForm):
    scores = forms.MultipleChoiceField(required=True,
                                       widget=forms.CheckboxSelectMultiple,
                                       choices=SCORES_CHOICES,
                                       label=_('Scores'))

    scores.initial = (1, 2)

    min_answers = forms.ChoiceField(label=_("Min answers"), required=True)
    max_answers = forms.ChoiceField(label=_("Max answers"), required=True)
    def __init__(self, *args, **kwargs):
        super(ScoresForm, self).__init__(*args, **kwargs)
        if type(self.data) != dict:
            myDict = dict(self.data.iterlists())
        else:
            myDict = self.data

        if 'form-0-scores' in myDict: 
            self._scores_len = len(myDict['form-0-scores'])
        elif 'scores' in self.initial:
            self._scores_len = len(self.initial['scores'])
        else:
            self._scores_len = SCORES_DEFAULT_LEN
        max_choices = map(lambda x: (x,x), range(1, self._scores_len + 1))
        self.fields['max_answers'].choices = max_choices
        self.fields['max_answers'].initial = self._scores_len
        self.fields['min_answers'].choices = max_choices


    def clean(self):
        super(ScoresForm, self).clean()
        max_answers = int(self.cleaned_data.get('max_answers', 0))
        min_answers = int(self.cleaned_data.get('min_answers', 0))
        if (min_answers and max_answers) and min_answers > max_answers:
            raise forms.ValidationError(_("Max answers should be greater "
                                          "or equal to min answers"))
        answer_list = []
        for key in self.cleaned_data:
            if key.startswith('answer_'):
                if '%' in self.cleaned_data[key]:
                    raise forms.ValidationError(_("&#37; is not a valid character"))
                answer_list.append(self.cleaned_data[key])
        if len(answer_list) > len(set(answer_list)):
            raise forms.ValidationError(_("No duplicate choices allowed"))
        if 'scores' in self.cleaned_data:
            if (len(answer_list) < max_answers):
                m = _("Number of answers must be equal or bigger than max answers")
                raise forms.ValidationError(m)
        return self.cleaned_data


class RequiredFormset(BaseFormSet):

    def __init__(self, *args, **kwargs):
            super(RequiredFormset, self).__init__(*args, **kwargs)
            try:
                self.forms[0].empty_permitted = False
            except IndexError:
                pass

class CandidateWidget(MultiWidget):

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', [])
        widgets = (TextInput(),
                   Select(choices=departments))
        super(CandidateWidget, self).__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if not value:
            return [None, None]

        return json.loads(value)

    def format_output(self, rendered_widgets):
        """
        Given a list of rendered widgets (as strings), it inserts an HTML
        linebreak between them.

        Returns a Unicode string representing the HTML for the whole lot.
        """
        return """
        <div class="row answer_input"><div class="columns nine">%s</div>
        <div class="columns two" placeholder="">%s</div>
        <div class="columns one">
        <a href="#" style="font-weight: bold; color:red"
        class="remove_answer">X</a>
        </div>
        </div>
        """ % (rendered_widgets[0], rendered_widgets[1])

    def value_from_datadict(self, data, files, name):
        datalist = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]
        return json.dumps(datalist)


class StvForm(QuestionBaseForm):

    def __init__(self, *args, **kwargs):
        deps = kwargs['initial']['departments_data'].split('\n')
        DEPARTMENT_CHOICES = []
        for dep in deps:
            DEPARTMENT_CHOICES.append((dep.strip(),dep.strip()))

        super(StvForm, self).__init__(*args, **kwargs)

        self.fields.pop('question')
        answers = len(filter(lambda k: k.startswith("%s-answer_" %
                                                self.prefix), self.data)) / 2
        if not answers:
            answers = len(filter(lambda k: k.startswith("answer_"),
                                 self.initial))
        if answers == 0:
            answers = DEFAULT_ANSWERS_COUNT

        self.fields.clear()
        for ans in range(answers):
            field_key = 'answer_%d' % ans
            field_key1 = 'department_%d' % ans
            self.fields[field_key] = forms.CharField(max_length=600,
                                              required=True,
                                              widget=CandidateWidget(departments=DEPARTMENT_CHOICES),
                                              label=('Candidate'))

        elig_help_text = _("set the eligibles count of the election")
        label_text = _("Eligibles count") 
        self.fields.insert(0, 'eligibles', forms.CharField(
                                                    label=label_text,
                                                    help_text=elig_help_text))
        widget=forms.CheckboxInput(attrs={'onclick':'enable_limit()'})
        limit_help_text = _("enable limiting the elections from the same constituency")
        limit_label = _("Limit elected per constituency") 
        self.fields.insert(1,'has_department_limit',
                            forms.BooleanField(
                                                widget=widget,
                                                help_text=limit_help_text,
                                                label = limit_label,
                                                required=False))
        widget=forms.TextInput(attrs={'hidden': 'True'})
        dep_lim_help_text = _("maximum number of elected from the same constituency")
        dep_lim_label = _("Constituency limit")
        self.fields.insert(2, 'department_limit',
                            forms.CharField(
                                            help_text=dep_lim_help_text,
                                            label=dep_lim_label,
                                            widget=widget,
                                            required=False))

    min_answers = None
    max_answers = None

    def clean(self):
        from django.forms.util import ErrorList
        message = _("This field is required.")
        answers = len(filter(lambda k: k.startswith("%s-answer_" %
                                                self.prefix), self.data)) / 2
        #list used for checking duplicate candidates
        candidates_list = []

        for ans in range(answers):
            field_key = 'answer_%d' % ans
            answer = self.cleaned_data[field_key]
            answer_lst = json.loads(answer)
            if '%' in answer_lst[0]:
                raise forms.ValidationError(_("&#37; is not a valid character"))
            candidates_list.append(answer_lst[0])
            if not answer_lst[0]:
                self._errors[field_key] = ErrorList([message])
            answer_lst[0] = answer_lst[0].strip()
            self.cleaned_data[field_key] = json.dumps(answer_lst)

        if len(candidates_list) > len(set(candidates_list)):
            raise forms.ValidationError(_("No duplicate choices allowed"))

        return self.cleaned_data

    def clean_eligibles(self):
        message = _("Value must be a positve integer")
        eligibles = self.cleaned_data.get('eligibles')
        try:
            eligibles = int(eligibles)
            if eligibles > 0:
                return eligibles
            else:
                raise forms.ValidationError(message)
        except ValueError,TypeError:
            raise forms.ValidationError(message)

    def clean_department_limit(self):
        message = _("Value must be a positve integer")
        dep_limit = self.cleaned_data.get('department_limit')
        if self.cleaned_data.get('has_department_limit'):
            if not dep_limit:
                raise forms.ValidationError(message)
        else:
            return 0
        try:
            dep_limit = int(dep_limit)
            if dep_limit > 0:
                return dep_limit
            else:
                raise forms.ValidationError(message)
        except ValueError:
            raise forms.ValidationError(message)

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
        
        if user.is_disabled:
            raise forms.ValidationError(_("Your account is disabled"))

        if check_password(password, user.info['password']):
            self._user_cache = user
            return self.cleaned_data
        else:
            raise forms.ValidationError(_("Invalid username or password"))


class PollForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.election = kwargs.pop('election', None)
        super(PollForm, self).__init__(*args, **kwargs)
        CHOICES = (
            ('public', 'public'),
            ('confidential', 'confidential'),
        )
        self.fields['oauth2_client_type'] = forms.ChoiceField(required=False,
                                                              choices=CHOICES)
        if self.election.feature_frozen:
            self.fields['name'].widget.attrs['readonly'] = True
    
    class Meta:
        model = Poll
        fields = ('name', 'oauth2_thirdparty', 'oauth2_client_type',
                  'oauth2_client_id', 'oauth2_client_secret', 'oauth2_url',)
       
    def clean(self):

        data = self.cleaned_data
        election_polls = self.election.polls.all()
        for poll in election_polls:
            if data['name'] == poll.name and not self.instance.pk:
                message = _("Duplicate poll names are not allowed")
                raise forms.ValidationError(message)

        if self.election.feature_frozen and\
            (self.cleaned_data['name'] != self.instance.name):
                raise forms.ValidationError("can't touch this")
        
        field_names = ['client_type', 'client_id', 'client_secret', 'url']
        field_names = ['oauth2_' + x for x in field_names]
        url_validate = URLValidator()
        if data['oauth2_thirdparty']:
            for field_name in field_names:
                if not data[field_name]:
                    self._errors[field_name] = 'required!'
            try:
                url_validate(data['oauth2_url'])
            except ValidationError:
                self._errors['oauth2_url'] = "Invalid URL"
        else:
            for field_name in field_names:
                data[field_name] = ''

        return data

    def save(self, *args, **kwargs):
        instance = super(PollForm, self).save(commit=False, *args, **kwargs)
        instance.election = self.election
        instance.save()
        return instance


class PollFormSet(BaseModelFormSet):

    def __init__(self, *args, **kwargs):
        self.election = kwargs.pop('election', None)
        super(PollFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        forms_data = self.cleaned_data
        form_poll_names = []
        for form_data in forms_data:
            form_poll_names.append(form_data['name'])
            poll_name = form_data['name']
            e = Election.objects.get(id=self.election.id)
            election_polls = e.polls.all()
            for poll in election_polls:
                if poll_name == poll.name:
                    message = _("Duplicate poll names are not allowed")
                    raise forms.ValidationError(message)
        if len(form_poll_names) > len(set(form_poll_names)):
            message = _("Duplicate poll names are not allowed")
            raise forms.ValidationError(message)
 
    def save(self, election, *args, **kwargs):
        instances = super(PollFormSet, self).save(*args, commit=False,
                                                  **kwargs)
        for instance in instances:
            instance.election = election
            instance.save()

        return instances


SEND_TO_CHOICES = [
    ('all', _('all selected voters')),
    ('voted', _('selected voters who have cast a ballot')),
    ('not-voted', _('selected voters who have not yet cast a ballot'))
]

class EmailVotersForm(forms.Form):
    subject = forms.CharField(label=_('Email subject'), max_length=80,
                              required=False)
    body = forms.CharField(label=_('In place of BODY'), max_length=30000,
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


class VoterLoginForm(forms.Form):

    login_id = forms.CharField(label=_('Login password'), required=True)

    def __init__(self, *args, **kwargs):
        self._voter = None
        super(VoterLoginForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(VoterLoginForm, self).clean()

        login_id = self.cleaned_data.get('login_id')

        invalid_login_id_error = _("Invalid login code")
        if not login_id:
            raise forms.ValidationError(invalid_login_id_error)

        try:
            poll_id, secret = login_id.split("-", 1)
            secret = undecalize(secret)
        except ValueError:
            raise forms.ValidationError(invalid_login_id_error)

        poll = None
        try:
            poll = Poll.objects.get(pk=poll_id)
        except Poll.DoesNotExist:
            raise forms.ValidationError(invalid_login_id_error)

        try:
            self._voter = poll.voters.get(voter_password=secret)
        except Voter.DoesNotExist:
            raise forms.ValidationError(_("Invalid email or password"))

        return cleaned_data
