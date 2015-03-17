"""
Forms for Helios
"""

from django import forms
from django.forms import ModelForm
from models import Election, Key, Signature
from django.conf import settings


class ElectionForm(forms.Form):
  name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'data-help': 'The pretty name for your election, e.g. \"My Club 2010 Election\".'}))
  short_name = forms.SlugField(label='Short Name', max_length=25, widget=forms.TextInput(attrs={'data-help': 'No spaces, will be part of the URL for your election, e.g. \"my-club-2010\".'}))
  election_type = forms.ChoiceField(label='Election Type', choices=Election.ELECTION_TYPES, widget=forms.Select())
  use_voter_aliases = forms.BooleanField(required=False, initial=False, label='Use Voter Aliases', widget=forms.CheckboxInput(attrs={'data-help': 'If selected, voter identities will be replaced with aliases, e.g. \"V12\", in the ballot tracking center.'}))
  #use_advanced_audit_features = forms.BooleanField(required=False, initial=True, help_text='disable this only if you want a simple election with reduced security but a simpler user interface')
  randomize_answer_order = forms.BooleanField(required=False, initial=False, label='Randomize Answer Order', widget=forms.CheckboxInput(attrs={'data-help': 'Enable this if you want the answers to questions to appear in random order for each voter.'}))
  private_p = forms.BooleanField(required=False, initial=False, label='Private', widget=forms.CheckboxInput(attrs={'data-help': 'A private election is only visible to registered voters.'}))
  use_threshold = forms.BooleanField(required=False, initial=False, label='Use Threshold Encryption', widget=forms.CheckboxInput(attrs={'data-help': 'When threshold encryption is used, only a specific number of trustees is required to present their private key to decrypt the result.'}))
  voting_starts_at = forms.DateTimeField(required=False, label='Voting Starts at', widget=forms.TextInput(attrs={'class': 'datetimepicker', 'data-help': 'Date and time when voting starts.'}))
  voting_ends_at = forms.DateTimeField(required=False, label='Voting Ends at', widget=forms.TextInput(attrs={'class': 'datetimepicker', 'data-help': 'Date and time when voting ends.'}))
  publish_tally_at = forms.DateTimeField(required=False, label='Publish Tally at', widget=forms.TextInput(attrs={'class': 'datetimepicker', 'data-help': 'Date and time when all voters will be able to view the tally.'}))
  help_email = forms.CharField(required=False, initial='', label='Help E-mail Address', widget=forms.TextInput(attrs={'data-help': 'An e-mail address voters should contact if they need help.'}))
  description = forms.CharField(max_length=4000, widget=forms.Textarea(), required=False)
  if settings.ALLOW_ELECTION_INFO_URL:
    election_info_url = forms.CharField(required=False, initial='', label='Election Info Download URL', help_text='The URL of a PDF document that contains extra election information, e.g. candidate bios and statements.')


class ElectionEditForm(ElectionForm):
  def __init__(self, *args, **kwargs):
    super(ElectionEditForm, self).__init__(*args, **kwargs)
    self.fields.pop('use_threshold')


class EmailVotersForm(forms.Form):
  subject = forms.CharField(required=False, max_length=80)
  body = forms.CharField(required=False, max_length=4000, widget=forms.Textarea)
  send_to = forms.ChoiceField(label='Send To', initial='all', choices=[('all', 'All Voters'), ('voted', 'Voters Who Have Cast a Ballot'), ('not-voted', 'Voters Who Have Not Yet Cast a Ballot')])


class ElectionTimesForm(forms.Form):
  voting_starts_at = forms.DateTimeField(required=False, label='Voting Starts at', widget=forms.TextInput(attrs={'class': 'datetimepicker', 'data-help': 'Date and time when voting starts.'}))
  voting_ends_at = forms.DateTimeField(required=False, label='Voting Ends at', widget=forms.TextInput(attrs={'class': 'datetimepicker', 'data-help': 'Date and time when voting ends.'}))


class TallyNotificationEmailForm(forms.Form):
  subject = forms.CharField(max_length=80)
  body = forms.CharField(
    max_length=2000, widget=forms.Textarea, required=False)
  send_to = forms.ChoiceField(label='Send To', choices=[('all', 'all voters'), ('voted', 'only voters who cast a ballot'), ('none', 'no one -- are you sure about this?')])


class ThresholdSchemeForm(forms.Form):
  k = forms.IntegerField(label='Number of Trustees')


class VoterPasswordForm(forms.Form):
  voter_id = forms.CharField(max_length=50, label='Voter ID')
  password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


class KeyForm(ModelForm):
  class Meta:
    model = Key


class kForm(forms.Form):
  k = forms.IntegerField()


class SignatureForm(ModelForm):
  class Meta:
    model = Signature
