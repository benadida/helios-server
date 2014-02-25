"""
Forms for Helios
"""

from django import forms
from models import Election
from widgets import *
from fields import *

class ElectionForm(forms.Form):
  short_name = forms.SlugField(max_length=25, help_text='No spaces, will be part of the URL for your election, e.g. my-club-2010')
  name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'size':60}), help_text='The pretty name for your election, e.g. My Club 2010 Election')
  description = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={'cols': 70, 'wrap': 'soft'}), required=False)
  election_type = forms.ChoiceField(label="Type:", choices = Election.ELECTION_TYPES)
  use_voter_aliases = forms.BooleanField(required=False, initial=False, help_text='If selected, voter identities will be replaced with aliases, e.g. "V12", in the ballot tracking center')
  #use_advanced_audit_features = forms.BooleanField(required=False, initial=True, help_text='disable this only if you want a simple election with reduced security but a simpler user interface')
  randomize_answer_order = forms.BooleanField(required=False, initial=False, help_text='Enable this if you want the answers to questions to appear in random order for each voter')
  private_p = forms.BooleanField(required=False, initial=False, label="Private?", help_text='A private election is only visible to registered voters.')
  use_threshold = forms.BooleanField(required=False, initial=False,label="Use threshold encryption?", help_text = 'Using threshold encryption allows a subset of k out of n trustees to decrypt the tally')
  help_email = forms.CharField(required=False, label="Help e-mail address:", help_text='An email address voters should contact if they need help')

class ElectionTimesForm(forms.Form):
  # Times
  voting_starts_at = SplitDateTimeField(help_text = 'UTC date and time when voting begins', widget=SplitSelectDateTimeWidget)
  voting_ends_at = SplitDateTimeField(help_text = 'UTC date and time when voting ends', widget=SplitSelectDateTimeWidget)

class EmailVotersForm(forms.Form):
  subject = forms.CharField(max_length=80)
  body = forms.CharField(max_length=2000, widget=forms.Textarea)
  send_to = forms.ChoiceField(label="Send To", initial="all", choices= [('all', 'all voters'), ('voted', 'voters who have cast a ballot'), ('not-voted', 'voters who have not yet cast a ballot')])

class TallyNotificationEmailForm(forms.Form):
  subject = forms.CharField(max_length=80)
  body = forms.CharField(max_length=2000, widget=forms.Textarea, required=False)
  send_to = forms.ChoiceField(label="Send To", choices= [('all', 'all voters'), ('voted', 'only voters who cast a ballot'), ('none', 'no one -- are you sure about this?')])

class VoterPasswordForm(forms.Form):
  voter_id = forms.CharField(max_length=50, label="Voter ID")
  password = forms.CharField(widget=forms.PasswordInput(), max_length=100)

