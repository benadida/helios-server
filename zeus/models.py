from django.db import models

class Institution(models.Model):
    name = models.CharField(max_length=255)
    ecounting_id = models.CharField(max_length=255)

class ElectionInfo(models.Model):
    uuid = models.CharField(max_length=50, null=False)
    stage = models.CharField(max_length=32)

    @property
    def election(self):
        from helios import models as helios_models
        return helios_models.Election.objects.get(uuid=self.uuid)

