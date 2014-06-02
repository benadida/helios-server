from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _

from helios_auth.models import User
from helios_auth.jsonfield import JSONField

class HeliosLog(models.Model):
	user = models.ForeignKey(User)
	model = models.CharField(max_length=200, null=True) # model name
	#log description
	description = JSONField()
	at = models.DateTimeField(auto_now_add=True)
	ip = models.IPAddressField(null=True)

	ACTION_TYPES = (
		('ADD', _('Add')),
		('DEL', _('Delete')),
		('MODIFY', _('Modify'))
	)
	
	action_type = models.CharField(max_length=250, null=False, default='MODIFY',
		choices = ACTION_TYPES)

	def __unicode__(self):
			return self.user
