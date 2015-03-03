from django.db import models
from django.utils.translation import ugettext as _

# Create your models here.
class Institution(models.Model):
  
  name = models.CharField(max_length=250)
  short_name = models.CharField(max_length=100, blank=True)
  main_phone = models.CharField(max_length=25)
  sec_phone = models.CharField(max_length=25, blank=True)
  address = models.TextField()
  mngt_email = models.EmailField()
  
  class Meta:
    permissions = (
        ("delegate_institution_mngt", _("Can delegate institution management tasks")),
        ("revoke_institution_mngt", _("Can revoke institution management tasks")),
        ("delegate_election_mngt", _("Can delegate election management tasks")),
        ("revoke_election_mngt", _("Can revoke election management tasks")),
    )
