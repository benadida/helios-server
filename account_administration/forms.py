from django import forms
from django.forms import ModelForm
from django.utils.translation import ugettext as _

from heliosauth.models import User
from zeus.models.zeus_models import Institution


class userForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(userForm, self).__init__(*args, **kwargs)
        self.fields['user_id'].label = "User ID"
        self.fields['name'].label = _("Name")
        self.fields['institution'].label = _("Institution")
    name = forms.CharField(required=False)
    institution = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ['user_id']


class institutionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(institutionForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _("Name")

    class Meta:
        model = Institution
        fields = ['name']
