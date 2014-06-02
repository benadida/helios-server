from django.contrib import admin

from helioslog.models import HeliosLog

class HeliosLogAdmin(admin.ModelAdmin):
	readonly_fields = ('user', 'model', 'ip', 'at', 'description', 'action_type')
	

admin.site.register(HeliosLog,HeliosLogAdmin)