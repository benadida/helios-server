from django.db import migrations, models


def transfer_unsent(apps, schema_editor):
    mail = apps.get_model('helios', 'VoteConfirmationEmail').objects.using(schema_editor.connection.alias)
    mail.filter(provider='resend', attempts=0, first_attempt_at=None, attempted_at=None).exclude(state='sent').update(provider='sendbyte')
    # A timeout may have occurred after Resend accepted the message. A new
    # provider cannot deduplicate that send; leave it for operator review.
    mail.filter(provider='resend').exclude(state='sent').update(state='review_required', lease=None)


class Migration(migrations.Migration):
    dependencies = [('helios', '0015_vote_confirmation_email')]
    operations = [
        migrations.AddField(model_name='voteconfirmationemail', name='provider',
                            field=models.CharField(max_length=20, default='resend')),
        migrations.RunPython(transfer_unsent, migrations.RunPython.noop),
        migrations.AlterField(model_name='voteconfirmationemail', name='provider',
                              field=models.CharField(max_length=20, default='sendbyte')),
    ]
