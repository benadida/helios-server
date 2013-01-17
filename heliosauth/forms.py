from django import forms
from django.utils.translation import ugettext_lazy as _

class ChangePasswordForm(forms.Form):
    password = forms.CharField(label=_('Current password'), widget=forms.PasswordInput)
    new_password = forms.CharField(label=_('New password'), widget=forms.PasswordInput)
    new_password_confirm = forms.CharField(label=_('New password confirm'), widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def save(self):
        user = self.user
        user.info['password'] = self.cleaned_data['new_password'].strip()
        user.save()

    def clean(self):
        cl = super(ChangePasswordForm, self).clean()
        if not self.user.info['password'] == self.cleaned_data.get('password'):
            raise forms.ValidationError(_('Invalid password'))
        if not self.cleaned_data.get('new_password') == \
           self.cleaned_data.get('new_password_confirm'):
            raise forms.ValidationError(_('Passwords don\'t match'))
        return cl


