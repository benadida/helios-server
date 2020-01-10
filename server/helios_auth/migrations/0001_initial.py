# -*- coding: utf-8 -*-


from django.db import models, migrations
import helios_auth.jsonfield


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user_type', models.CharField(max_length=50)),
                ('user_id', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=200, null=True)),
                ('info', helios_auth.jsonfield.JSONField()),
                ('token', helios_auth.jsonfield.JSONField(null=True)),
                ('admin_p', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='user',
            unique_together=set([('user_type', 'user_id')]),
        ),
    ]
