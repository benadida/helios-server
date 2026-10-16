import datetime
import uuid
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('helios', '0014_vote_verification_job')]
    operations = [migrations.CreateModel(name='VoteConfirmationEmail', fields=[
        ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
        ('payload', models.JSONField()),
        ('state', models.CharField(default='pending', max_length=20)),
        ('attempts', models.PositiveIntegerField(default=0)),
        ('first_attempt_at', models.DateTimeField(null=True)),
        ('attempted_at', models.DateTimeField(null=True)),
        ('next_attempt_at', models.DateTimeField(default=datetime.datetime.utcnow, db_index=True)),
        ('sent_at', models.DateTimeField(null=True)),
        ('lease', models.UUIDField(null=True)),
        ('cast_vote', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='confirmation_email', to='helios.castvote')),
    ])]
