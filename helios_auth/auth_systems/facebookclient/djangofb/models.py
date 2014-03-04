from django.db import models
from django.utils.html import escape
from django.utils.safestring import mark_safe

FB_MESSAGE_STATUS = (
    (0, 'Explanation'),
    (1, 'Error'),
    (2, 'Success'),
)


class MessageManager(models.Manager):

    def get_and_delete_all(self, uid):
        messages = []
        for m in self.filter(uid=uid):
            messages.append(m)
            m.delete()
        return messages


class Message(models.Model):

    """Represents a message for a Facebook user."""
    uid = models.CharField(max_length=25)
    status = models.IntegerField(choices=FB_MESSAGE_STATUS)
    message = models.CharField(max_length=300)
    objects = MessageManager()

    def __unicode__(self):
        return self.message

    def _fb_tag(self):
        return self.get_status_display().lower()

    def as_fbml(self):
        return mark_safe(u'<fb:%s message="%s" />' % (
            self._fb_tag(),
            escape(self.message),
        ))
