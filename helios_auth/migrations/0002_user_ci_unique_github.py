from django.db import migrations, models
from django.db.models import Count, Q
from django.db.models.functions import Lower


def check_no_case_duplicates(apps, schema_editor):
  User = apps.get_model('helios_auth', 'User')
  duplicates = (User.objects.filter(user_type='github')
                .values(lower_user_id=Lower('user_id'))
                .annotate(n=Count('id')).filter(n__gt=1))
  if duplicates.exists():
    raise RuntimeError(
      "%d GitHub user_id(s) exist in multiple casings. "
      "Run `python manage.py merge_duplicate_users` first, then re-run migrate."
      % duplicates.count())


class Migration(migrations.Migration):

  dependencies = [
    ('helios_auth', '0001_initial'),
  ]

  operations = [
    migrations.RunPython(check_no_case_duplicates, migrations.RunPython.noop),
    migrations.AddConstraint(
      model_name='user',
      constraint=models.UniqueConstraint(models.functions.Lower('user_id'), 'user_type',
                                         condition=Q(user_type='github'),
                                         name='helios_auth_user_ci_unique_github'),
    ),
  ]
