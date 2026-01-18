# Generated manually for soft delete functionality

from django.db import migrations, models


class Migration(migrations.Migration):

  dependencies = [
    ('helios', '0007_add_election_admins'),
  ]

  operations = [
    migrations.AddField(
      model_name='election',
      name='deleted_p',
      field=models.BooleanField(default=False, null=False),
    ),
    migrations.AddField(
      model_name='election',
      name='deleted_at',
      field=models.DateTimeField(default=None, null=True),
    ),
  ]
