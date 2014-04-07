from django.contrib import admin
from helios.models import User

class UserAdmin(admin.ModelAdmin):	
    exclude = ('info', 'token')

admin.site.register(User, UserAdmin)