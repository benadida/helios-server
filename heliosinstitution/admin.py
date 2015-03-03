from django.contrib import admin

from heliosinstitution.models import Institution


# Register your models here.
class HeliosInstitutionAdmin(admin.ModelAdmin):	
	fields = ('short_name', 'name', 'address', 'main_phone', 'sec_phone', 'mngt_email')
	list_display = ('name', 'short_name', 'main_phone', 'mngt_email')


admin.site.register(Institution, HeliosInstitutionAdmin)
