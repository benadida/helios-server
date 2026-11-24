import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helios', '0012_site_announcement'),
    ]

    operations = [
        # cast_at now holds the time the server received the ballot, which the
        # view assigns; auto_now_add would replace it with the confirmation time
        migrations.AlterField(
            model_name='castvote',
            name='cast_at',
            field=models.DateTimeField(default=datetime.datetime.utcnow),
        ),
    ]
