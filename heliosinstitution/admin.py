from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext, ugettext_lazy as _


from heliosinstitution.models import Institution, InstitutionUserProfile


class HeliosInstitutionAdmin(admin.ModelAdmin):	
	list_display = ('name', 'short_name', 'main_phone')
	readonly_fields = ('idp_address',)


class InstitutionUserProfileAdmin(admin.ModelAdmin):	
    list_display = ('helios_user', 'email', 'institution')


class UserAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('username',)}),
        (_('Permissions'), {'fields': ('groups', )}),
    )


admin.site.register(InstitutionUserProfile, InstitutionUserProfileAdmin)
admin.site.register(Institution, HeliosInstitutionAdmin)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
