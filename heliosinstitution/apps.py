from django.apps import AppConfig
from django.db.models import signals

from heliosinstitution import signals as helios_institution_signals

class HeliosInstitutionConfig(AppConfig):
    name = 'heliosinstitution'
    verbose_name = "Helios Institution"

    def ready(self):
        signals.post_migrate.connect(
                helios_institution_signals.update_permissions_after_migration,
                sender=self)