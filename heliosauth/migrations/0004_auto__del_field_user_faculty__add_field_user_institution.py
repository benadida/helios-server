# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'User.faculty'
        db.delete_column('heliosauth_user', 'faculty_id')

        # Adding field 'User.institution'
        db.add_column('heliosauth_user', 'institution',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zeus.Institution'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'User.faculty'
        db.add_column('heliosauth_user', 'faculty',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zeus.Faculty'], null=True),
                      keep_default=False)

        # Deleting field 'User.institution'
        db.delete_column('heliosauth_user', 'institution_id')


    models = {
        'heliosauth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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