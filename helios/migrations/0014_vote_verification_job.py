import datetime

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('helios', '0013_shared_request_limits')]
    operations = [migrations.CreateModel(
        name='VoteVerificationJob',
        fields=[
            ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('state', models.CharField(choices=[('pending', 'Pending'), ('complete', 'Complete'),
                ('failed', 'Needs attention')], default='pending', max_length=10)),
            ('attempts', models.PositiveSmallIntegerField(default=0)),
            ('next_attempt_at', models.DateTimeField(default=datetime.datetime.utcnow)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('completed_at', models.DateTimeField(null=True)),
            ('last_error_code', models.CharField(blank=True, default='', max_length=80)),
            ('cast_vote', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                related_name='verification_job', to='helios.castvote')),
        ],
        options={'indexes': [models.Index(condition=models.Q(state='pending'),
            fields=['next_attempt_at', 'id'], name='helios_vjob_pending_idx')]},
    )]
