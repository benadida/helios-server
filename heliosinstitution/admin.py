from django.contrib import admin

from heliosinstitution.models import Institution, InstitutionUserProfile


class HeliosInstitutionAdmin(admin.ModelAdmin):	
	list_display = ('name', 'short_name', 'main_phone')
	readonly_fields = ('idp_address',)


class InstitutionUserProfileAdmin(admin.ModelAdmin):	
    list_display = ('helios_user', 'email', 'institution')


admin.site.register(InstitutionUserProfile, InstitutionUserProfileAdmin)
admin.site.register(Institution, HeliosInstitutionAdmin)
