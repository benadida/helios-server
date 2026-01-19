# Generated for adding index on deleted_at field

from django.db import migrations, models


class Migration(migrations.Migration):

  dependencies = [
    ('helios', '0008_add_election_soft_delete'),
  ]

  operations = [
    migrations.AlterField(
      model_name='election',
      name='deleted_at',
      field=models.DateTimeField(default=None, null=True, db_index=True, auto_now_add=False),
    ),
  ]
