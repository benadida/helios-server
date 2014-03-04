from django.db import models

from helios.datatypes.djangofield import LDObjectField
from django.forms import ModelForm
from helios import utils
from django import forms
import thresholdalgs
from django.core.files.storage import FileSystemStorage
from helios.models import *

# Create your models here.


class Key(models.Model):

    name = models.CharField(max_length=40)
    email = models.CharField(max_length=60)
    #pub_date = models.DateTimeField('date published')
    #public_key = LDObjectField(type_hint = 'legacy/EGPublicKey',null=True)
    public_key_encrypt = models.CharField(max_length=10000)
    public_key_signing = models.CharField(max_length=10000)
    pok_encrypt = models.CharField(max_length=10000)
    pok_signing = models.CharField(max_length=10000)
    public_key_encrypt_hash = models.CharField(max_length=100)
    public_key_signing_hash = models.CharField(max_length=100)


class KeyForm(ModelForm):

    class Meta:
        model = Key


class SecretKey(models.Model):
    public_key = models.ForeignKey(Key)
    secret_key_encrypt = models.CharField(max_length=10000, null=True)
    secret_key_signing = models.CharField(max_length=10000, null=True)


class kForm(forms.Form):
    k = forms.IntegerField()


class Signed_Encrypted_Share(models.Model):
    election_id = models.IntegerField()
    share = models.CharField(max_length=10000000)
    signer = models.CharField(max_length=40)
    signer_id = models.IntegerField()
    receiver = models.CharField(max_length=40)
    receiver_id = models.IntegerField()
    trustee_signer_id = models.IntegerField()
    trustee_receiver_id = models.IntegerField()


class Signature(models.Model):
    signature = models.CharField(max_length=10000)


class SignatureForm(ModelForm):

    class Meta:
        model = Signature


class Ei(models.Model):
    election_id = models.IntegerField()
    value = models.CharField(max_length=10000)
    signer_id = models.IntegerField()
    signer = models.CharField(max_length=40)


class Incorrect_share(models.Model):
    share = models.CharField(max_length=100000)
    election_id = models.IntegerField()
    sig = models.CharField(max_length=100000)
    signer_id = models.IntegerField()

    receiver_id = models.IntegerField()
    explanation = models.CharField(max_length=200)


# class RadioForm(forms.Form,n):
#
#    CHOICES = []
#    for i in range(n):
#        CHOICES.append((i+1,str(i+1)))
#
#    choice = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect())
#
