from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from helios import models as helios_models

from zeus.core import get_random_int


class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    ecounting_id = models.CharField(max_length=255)
    is_disabled = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

    class Meta:
        app_label = 'zeus'


class ElectionInfo(models.Model):
    uuid = models.CharField(max_length=50, null=False)
    _election = None

    @property
    def election(self):
        if self._election:
            return self._election
        else:
            self._election = helios_models.Election.objects.get(uuid=self.uuid)
            return self._election

    class Meta:
        app_label = 'zeus'


class SecretAuthcode(models.Model):
    code = models.CharField(max_length=63, primary_key=True)
    election_uuid = models.CharField(max_length=50, null=False)
    voter_login = models.CharField(max_length=50, null=False)

    class Meta:
        unique_together = ('election_uuid', 'voter_login')
        app_label = 'zeus'



def generate_authcodes(election_uuid, voter_logins=()):
    if not voter_logins:
        e = helios_models.Election.objects.get(uuid=election_uuid)
        voter_logins = e.voter_set.values_list('voter_login_id', flat=True)

    create = SecretAuthcode.objects.create
    for voter_login in voter_logins:
        create(code=generate_authcode(12), election_uuid=election_uuid,
               voter_login=voter_login)


def list_authcodes(election_uuid, voter_logins=()):
    if not voter_logins:
        listing = SecretAuthcode.objects.filter(election_uuid=election_uuid)
    else:
        listing = SecretAuthcode.objects.filter(election_uuid=election_uuid,
                                                voter_login__in=voter_logins)
    listing = listing.values_list('voter_login', 'code')
    return listing


def lookup_authcode(code):
    try:
        authcode = SecretAuthcode.objects.get(code=code)
        return authcode.election_uuid, authcode.voter_login
    except SecretAuthcode.DoesNotExist:
        return None


def purge_authcodes(election_uuid, voter_logins=()):
    if not voter_logins:
        SecretAuthcode.objects.filter(election_uuid=election_uuid).delete()
    else:
        SecretAuthcode.objects.filter(election_uuid=election_uuid,
                                      voter_login__in=voter_logins).delete()


def generate_authcode(length=12):
    #alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    r = get_random_int(0, 10 ** length)
    authcode = "%0*d" % (length, r)
    if len(authcode) != length:
        m = "Invalid authcode length"
        raise AssertionError(m)
    return authcode
