from django.contrib import admin
from helios.models import Voter, Election


class VoterAdmin(admin.ModelAdmin):	
	fields = ('user', 'vote_hash', 'cast_at', 'voter_email')
	readonly_fields = ('user', 'vote_hash', 'cast_at', 'voter_email')
	list_display = ('user', 'vote_hash', 'cast_at', 'voter_email')


class ElectionAdmin(admin.ModelAdmin):
	fields = ('admin', 'short_name', 'name', 'election_type',
	'openreg', 'use_voter_aliases', 'randomize_answer_order', 
	'frozen_at', 'tallying_started_at', 'tallying_finished_at',
	'help_email', 'election_info_url', 'result', 'featured_p')
	readonly_fields = ('admin', 'short_name', 'name', 'election_type',
	'openreg', 'use_voter_aliases', 'randomize_answer_order', 
	'frozen_at', 'tallying_started_at', 'tallying_finished_at', 'help_email',
	'election_info_url', 'result')
	list_display = ('admin', 'name', 'election_type', 'featured_p')

admin.site.register(Voter, VoterAdmin)
admin.site.register(Election, ElectionAdmin)