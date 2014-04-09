from django.contrib import admin
from helios.models import Voter


class VoterAdmin(admin.ModelAdmin):	
    fields = ('user', 'vote_hash', 'cast_at', 'voter_email')
    readonly_fields = ('user', 'vote_hash', 'cast_at', 'voter_email')
    list_display = ('user', 'vote_hash', 'cast_at', 'voter_email')

admin.site.register(Voter, VoterAdmin)