# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'User'
        db.create_table('heliosauth_user', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('user_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('institution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zeus.Institution'], null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('info', self.gf('heliosauth.jsonfield.JSONField')()),
            ('token', self.gf('heliosauth.jsonfield.JSONField')(null=True)),
            ('admin_p', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('superadmin_p', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('ecounting_account', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('heliosauth', ['User'])

        # Adding unique constraint on 'User', fields ['user_type', 'user_id']
        db.create_unique('heliosauth_user', ['user_type', 'user_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'User', fields ['user_type', 'user_id']
        db.delete_unique('heliosauth_user', ['user_type', 'user_id'])

        # Deleting model 'User'
        db.delete_table('heliosauth_user')


    models = {
        'heliosauth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ecounting_account': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('heliosauth.jsonfield.JSONField', [], {}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zeus.Institution']", 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'superadmin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'token': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zeus.institution': {
            'Meta': {'object_name': 'Institution'},
            'ecounting_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['heliosauth']