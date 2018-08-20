"""
Forms for Helios
"""

from django import forms
from models import Election
from widgets import *
from fields import *
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class ElectionForm(forms.Form):
  short_name = forms.SlugField(max_length=40, label=_("Short name"),
    help_text=_('no spaces, will be part of the URL for your election, e.g. my-club-2010'))
  name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'size':60}),
    label=_("Name"), help_text=_('the pretty name for your election, e.g. My Club 2010 Election. Maximum of 250 characters.'))
  description = forms.CharField(max_length=4000, label=_("Description"),
    help_text=_("Maximum of 4000 characters. You can use the HTML tags: <p>, <h4>, <h5>, <h3>, <h2>, <br>, <u>."),
    widget=forms.Textarea(attrs={'wrap': 'soft', 'class': 'form-control'}), required=False)
  election_type = forms.ChoiceField(label=_("Type"), choices = Election.ELECTION_TYPES,
    widget=forms.HiddenInput(), initial=Election.ELECTION_TYPES[0][0], required=False)
  use_voter_aliases = forms.BooleanField(required=False, initial=True,
    label=_("Use voter aliases"), help_text=_('If selected, voter identities will be replaced with aliases, e.g. "V12", in the ballot tracking center'))
  use_advanced_audit_features = forms.BooleanField(required=False, initial=False,
    label = _("Use advanced audit features"),
    help_text=_('disable this only if you want a simple election with reduced security but a simpler user interface'))
  randomize_answer_order = forms.BooleanField(required=False, initial=False,
    label=_("Randomize answer order"), help_text=_('enable this if you want the answers to questions to appear in random order for each voter'))
  private_p = forms.BooleanField(required=False, initial=True, label=_("Private?"),
          help_text=_('A private election is only visible to registered voters.'))
  help_email = forms.CharField(required=False, initial="", label=_("Help Email Address"),
    help_text=_('An email address voters should contact if they need help.'),
    widget=forms.TextInput(attrs={'size':60}))

  if settings.ALLOW_ELECTION_INFO_URL:
    election_info_url = forms.CharField(required=False, initial="", label=_("Election Info Download URL"), help_text=_("the URL of a PDF document that contains extra election information, e.g. candidate bios and statements"))

    # times
  voting_starts_at = forms.DateTimeField(label = _("Voting starts at"),
    help_text = _('UTC date and time when voting begins'),
    input_formats=['%d/%m/%Y %H:%M'],
    widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'),
    required = False)
  voting_ends_at = forms.DateTimeField(help_text = _("UTC date and time when voting ends"),
    label = _("Voting ends at"),
    input_formats=['%d/%m/%Y %H:%M'],
    widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'),
    required=False)

  def clean(self):
    cleaned_data = super(ElectionForm, self).clean()
    election_type = cleaned_data.get("election_type")
    if election_type == '':
      cleaned_data['election_type'] = self.fields['election_type'].initial
    return cleaned_data


class ElectionTimesForm(forms.Form):
  # times
  voting_starts_at = forms.DateTimeField(label = _("Voting starts at"),
    help_text = _('UTC date and time when voting begins'),
    input_formats=['%d/%m/%Y %H:%M'],
    widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'),

    )
  voting_ends_at = forms.DateTimeField(help_text = _('UTC date and time when voting ends'),
    label = _("Voting ends at"),
    input_formats=['%d/%m/%Y %H:%M'],
    widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'))

class ElectionTimeExtensionForm(forms.Form):
  voting_extended_until = forms.DateTimeField(help_text = _("UTC date and time voting extended to"),
    label = _("Voting extended until"),
    input_formats=['%d/%m/%Y %H:%M'],
    widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'),
    required=False)

class EmailVotersForm(forms.Form):
  subject = forms.CharField(max_length=80, required=True)
  body = forms.CharField(max_length=4000, widget=forms.Textarea)
  send_to = forms.ChoiceField(label=_("Send To"), initial="all", choices= [('all', _('all voters')), ('voted', _('voters who have cast a ballot')), ('not-voted', _('voters who have not yet cast a ballot'))])


class TallyNotificationEmailForm(forms.Form):
  subject = forms.CharField(max_length=80)
  body = forms.CharField(max_length=2000, widget=forms.Textarea, required=False)
  send_to = forms.ChoiceField(label=_("Send To"), choices= [
    ('all', _('all voters')),
      ('voted', _('only voters who cast a ballot')),
      ('none', _('no one -- are you sure about this?'))])

class VoterPasswordForm(forms.Form):
  voter_id = forms.CharField(max_length=50, label=_("Voter ID"))
  password = forms.CharField(widget=forms.PasswordInput(), max_length=100)
