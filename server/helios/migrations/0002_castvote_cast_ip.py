# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='castvote',
            name='cast_ip',
            field=models.GenericIPAddressField(null=True),
            preserve_default=True,
        ),
    ]
