from django.contrib import admin
from helios.models import CastVote, Election


class CastVoteAdmin(admin.ModelAdmin):	
	fields = ('voter', 'vote_hash', 'cast_at', 'cast_ip')
	readonly_fields = ('voter', 'vote_hash', 'cast_at', 'cast_ip')
	list_display = ('voter', 'vote_hash', 'cast_at', 'cast_ip')


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

admin.site.register(CastVote, CastVoteAdmin)
admin.site.register(Election, ElectionAdmin)