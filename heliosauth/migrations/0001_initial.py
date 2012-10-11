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
            ('faculty', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zeus.Faculty'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('info', self.gf('heliosauth.jsonfield.JSONField')()),
            ('token', self.gf('heliosauth.jsonfield.JSONField')(null=True)),
            ('admin_p', self.gf('django.db.models.fields.BooleanField')(default=False)),
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
            'faculty': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zeus.Faculty']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('heliosauth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zeus.faculty': {
            'Meta': {'object_name': 'Faculty'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['heliosauth']