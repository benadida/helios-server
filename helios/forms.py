"""
Forms for Helios
"""

from django import forms
from models import Election
from bulletin_board.models import Signature
from widgets import *
from fields import *
from django.conf import settings


class ElectionForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'size': 60}), help_text='The pretty name for your election, e.g. My Club 2010 Election.')
    short_name = forms.SlugField(label='Slug', max_length=25, help_text='No spaces, will be part of the URL for your election, e.g. my-club-2010.')
    description = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={'cols': 70, 'wrap': 'soft'}), required=False)
    election_type = forms.ChoiceField(label='Election Type', choices=Election.ELECTION_TYPES)
    use_voter_aliases = forms.BooleanField(required=False, initial=False, label='Use Voter Aliases', help_text='If selected, voter identities will be replaced with aliases, e.g. "V12", in the ballot tracking center.')
    #use_advanced_audit_features = forms.BooleanField(required=False, initial=True, help_text='disable this only if you want a simple election with reduced security but a simpler user interface')
    randomize_answer_order = forms.BooleanField(required=False, initial=False, label='Randomize Answer Order', help_text='Enable this if you want the answers to questions to appear in random order for each voter.')
    private_p = forms.BooleanField(required=False, initial=False, label='Private', help_text='A private election is only visible to registered voters.')
    use_threshold = forms.BooleanField(required=False, initial=False, label='Use Threshold Encryption', help_text='Using threshold encryption allows a subset of trustees to decrypt the tally.')
    help_email = forms.CharField(required=False, initial='', label='Help E-mail Address', help_text='An e-mail address voters should contact if they need help.')

    if settings.ALLOW_ELECTION_INFO_URL:
        election_info_url = forms.CharField(required=False, initial='', label='Election Info Download URL', help_text='The URL of a PDF document that contains extra election information, e.g. candidate bios and statements.')


class ElectionTimesForm(forms.Form):
    # Times
    voting_starts_at = SplitDateTimeField(label='Voting Starts At', help_text='UTC date and time when voting begins', widget=SplitSelectDateTimeWidget)
    voting_ends_at = SplitDateTimeField(label='Votin Ends At', help_text='UTC date and time when voting ends', widget=SplitSelectDateTimeWidget)


class EmailVotersForm(forms.Form):
    subject = forms.CharField(max_length=80)
    body = forms.CharField(max_length=2000, widget=forms.Textarea)
    send_to = forms.ChoiceField(label='Send To', initial='all', choices=[('all', 'All Voters'), ('voted', 'Voters Who Have Cast a Ballot'), ('not-voted', 'Voters Who Have Not Yet Cast a Ballot')])


class SignatureForm(forms.ModelForm):
    class Meta:
        model = Signature


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
