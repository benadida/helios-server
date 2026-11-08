from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
  # build the index without blocking new cast votes
  atomic = False

  dependencies = [
    ('helios', '0010_add_query_indexes'),
  ]

  operations = [
    AddIndexConcurrently(
      model_name='castvote',
      index=models.Index(fields=['cast_at'], name='helios_cv_cast_at_idx'),
    ),
  ]
