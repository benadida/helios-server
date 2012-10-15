from django.db import models

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

