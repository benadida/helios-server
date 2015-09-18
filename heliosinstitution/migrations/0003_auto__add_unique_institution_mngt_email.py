# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'Institution', fields ['mngt_email']
        db.create_unique(u'heliosinstitution_institution', ['mngt_email'])


    def backwards(self, orm):
        # Removing unique constraint on 'Institution', fields ['mngt_email']
        db.delete_unique(u'heliosinstitution_institution', ['mngt_email'])


    models = {
        u'heliosinstitution.institution': {
            'Meta': {'object_name': 'Institution'},
            'address': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'main_phone': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'mngt_email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'sec_phone': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        }
    }

    complete_apps = ['heliosinstitution']
