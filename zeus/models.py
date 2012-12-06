from django.db import models
from zeus.core import get_random_int

class Institution(models.Model):
    name = models.CharField(max_length=255)
    ecounting_id = models.CharField(max_length=255)

class ElectionInfo(models.Model):
    uuid = models.CharField(max_length=50, null=False)
    stage = models.CharField(max_length=32)
    _election = None

    @property
    def election(self):
        if self._election:
          return self._election
        else:
          from helios import models as helios_models
          self._election = helios_models.Election.objects.get(uuid=self.uuid)
          return self._election

class SecretAuthcode(models.Model):
    code = models.CharField(max_length=63, primary_key=True)
    election_uuid = models.CharField(max_length=50, null=False)
    voter_login = models.CharField(max_length=50, null=False)

    class Meta:
        unique_together = ('election_uuid', 'voter_login')

def generate_authcodes(election_uuid, voter_logins=()):
    if not voter_logins:
        from helios import models as helios_models
        e = helios_models.Election.objects.get(uuid=election_uuid)
        voter_logins = e.voter_set.values_list('voter_login_id', flat=True)

    create = SecretAuthcode.objects.create
    for voter_login in voter_logins:
        authcode = create(code          =   generate_authcode(12),
                          election_uuid =   election_uuid,
                          voter_login   =   voter_login)

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
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    s = ''
    for x in xrange(length):
        s += alphabet[get_random_int(0, 32)]

    if len(s) != length:
        raise AssertionError()

    return s

