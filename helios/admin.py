from django.contrib import admin

from helios.models import CastVote, Election, Trustee, Voter



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


class TrusteeAdmin(admin.ModelAdmin):	
	readonly_fields = ('uuid', 'election','name', 'email', 'secret',)
	list_display = ('uuid', 'election', 'name', 'email', 'secret',)

class VoterAdmin(admin.ModelAdmin):
	readonly_fields = ('vote', 'vote_hash', 'user', 'cast_at')

admin.site.register(CastVote, CastVoteAdmin)
admin.site.register(Election, ElectionAdmin)
admin.site.register(Trustee, TrusteeAdmin)
admin.site.register(Voter, VoterAdmin)