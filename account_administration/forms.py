from django import forms
from django.forms import ModelForm
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError

from heliosauth.models import User
from heliosauth.auth_systems.password import make_password
from zeus.models.zeus_models import Institution

from generate_password import random_password

class userForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(userForm, self).__init__(*args, **kwargs)
        self.fields['user_id'].label = "User ID"
        self.fields['name'].label = _("Name")
        self.fields['institution'].label = _("Institution")
    name = forms.CharField(required=False)
    institution = forms.CharField(required=True)
    
    def clean_institution(self):
        inst_name = self.cleaned_data['institution']
        try:
            inst = Institution.objects.get(name=inst_name)
            if inst.is_disabled:
                message = _("Institution is disabled and cannot be used")
                raise ValidationError(message) 
            self.cleaned_data['institution'] = inst
            return self.cleaned_data['institution']
        except Institution.DoesNotExist:
            raise ValidationError(_('Institution does not exist'))

    def save(self, commit=True):
        instance = super(userForm, self).save(commit=False)
        try:
            User.objects.get(id=instance.id)
            if commit:
                instance.save()
            return instance, None
        except(User.DoesNotExist):
            instance.name = self.cleaned_data['name']
            password = random_password()
            instance.info = {'name': instance.name or instance.user_id,
                        'password': make_password(password)}
            instance.institution = self.cleaned_data['institution']
            instance.management_p = False
            instance.admin_p = True
            instance.user_type = 'password'
            instance.superadmin_p = False
            instance.ecounting_account = False
            if commit:
                instance.save()
            return instance, password
            

    class Meta:
        model = User
        fields = ['user_id', 'name', 'institution']


class institutionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(institutionForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _("Name")

    def clean_name(self):
        name = self.cleaned_data['name']
        try:
            inst = Institution.objects.get(name=name)
            if inst.is_disabled:
                message = _("Institution already exists and it is disabled")
                raise ValidationError(message) 
            else:
                message = _("Institution already exists")
                raise ValidationError(message)
        except Institution.DoesNotExist:
            inst = None
        if not inst:
            return self.cleaned_data['name']
    class Meta:
        model = Institution
        fields = ['name']
