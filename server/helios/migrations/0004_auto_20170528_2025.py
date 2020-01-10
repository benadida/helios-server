# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helios', '0003_auto_20160507_1948'),
    ]

    operations = [
        migrations.AlterField(
            model_name='election',
            name='help_email',
            field=models.EmailField(max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='trustee',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
