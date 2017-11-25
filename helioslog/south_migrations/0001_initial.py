# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'HeliosLog'
        db.create_table('helioslog_helioslog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios_auth.User'])),
            ('model', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('description', self.gf('helios_auth.jsonfield.JSONField')()),
            ('at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True)),
            ('action_type', self.gf('django.db.models.fields.CharField')(default='MODIFY', max_length=250)),
        ))
        db.send_create_signal('helioslog', ['HeliosLog'])


    def backwards(self, orm):
        # Deleting model 'HeliosLog'
        db.delete_table('helioslog_helioslog')


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helioslog.helioslog': {
            'Meta': {'object_name': 'HeliosLog'},
            'action_type': ('django.db.models.fields.CharField', [], {'default': "'MODIFY'", 'max_length': '250'}),
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('helios_auth.jsonfield.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"})
        }
    }

    complete_apps = ['helioslog']