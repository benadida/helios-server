from django.contrib import admin
from helios.models import User

class UserAdmin(admin.ModelAdmin):	
    exclude = ('info', 'token')
    list_display = ('name', 'user_id')

admin.site.register(User, UserAdmin)