from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _, string_concat

from helios_auth.models import User
from helios_auth.jsonfield import JSONField

class HeliosLog(models.Model):
    user = models.ForeignKey(User)
    model = models.CharField(max_length=200, null=True) # model name
    #log description
    description = JSONField()
    at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True)

    class Meta:
        app_label = 'helioslog'

    ACTION_TYPES = (
		('ADD', _('Add')),
		('DEL', _('Delete')),
		('MODIFY', _('Modify'))
	)

    action_type = models.CharField(max_length=250, null=False, default='MODIFY',
		choices = ACTION_TYPES)

    def __unicode__(self):
        obj_str = _(' object of ')
        return u'%s - %s%s%s' % (self.user.name, self.action_type, obj_str,
			self.model)

    @property
    def pretty_type(self):
        return dict(self.ACTION_TYPES)[self.action_type]

    @property
    def pretty_description(self):
        return_val = "<ul>"
        for key in self.description:
            return_val += "<li>%s : %s </li>" % (key, self.description[key])
            return_val += "</ul>"
        return return_val
