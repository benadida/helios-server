from django.db import migrations, models


class Migration(migrations.Migration):
  dependencies = [('helios_auth', '0001_initial')]
  operations = [migrations.CreateModel(name='BridgeLoginRequest', fields=[
    ('state_hash', models.CharField(max_length=64, primary_key=True, serialize=False)),
    ('session_hash', models.CharField(max_length=64)),
    ('election_id', models.CharField(max_length=50)),
    ('expires_at', models.DateTimeField(db_index=True)),
    ('consumed_at', models.DateTimeField(null=True)),
  ])]
