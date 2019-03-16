"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls import url

from helios.views import *

urlpatterns = [
    # election data that is cryptographically verified
    url(r'^$', one_election),

    # metadata that need not be verified
    url(r'^/meta$', one_election_meta),
    
    # edit election params
    url(r'^/edit$', one_election_edit),
    url(r'^/schedule$', one_election_schedule),
    url(r'^/extend$', one_election_extend),
    url(r'^/archive$', one_election_archive),
    url(r'^/copy$', one_election_copy),

    # badge
    url(r'^/badge$', election_badge),

    # adding trustees
    url(r'^/trustees/$', list_trustees),
    url(r'^/trustees/view$', list_trustees_view),
    url(r'^/trustees/new$', new_trustee),
    url(r'^/trustees/add-helios$', new_trustee_helios),
    url(r'^/trustees/delete$', delete_trustee),
    
    # trustee pages
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/home$', trustee_home),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/sendurl$', trustee_send_url),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/keygenerator$', trustee_keygenerator),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/check-sk$', trustee_check_sk),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/upoad-pk$', trustee_upload_pk),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/decrypt-and-prove$', trustee_decrypt_and_prove),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-decryption$', trustee_upload_decryption),
    
    # election voting-process actions
    url(r'^/view$', one_election_view),
    url(r'^/result$', one_election_result),
    url(r'^/result_proof$', one_election_result_proof),
    # url(r'^/bboard$', one_election_bboard),
    url(r'^/audited-ballots/$', one_election_audited_ballots),

    # get randomness
    url(r'^/get-randomness$', get_randomness),

    # server-side encryption
    url(r'^/encrypt-ballot$', encrypt_ballot),

    # construct election
    url(r'^/questions$', one_election_questions),
    url(r'^/set_reg$', one_election_set_reg),
    url(r'^/set_featured$', one_election_set_featured),
    url(r'^/save_questions$', one_election_save_questions),
    url(r'^/register$', one_election_register),
    url(r'^/freeze$', one_election_freeze), # includes freeze_2 as POST target
    
    # computing tally
    url(r'^/compute_tally$', one_election_compute_tally),
    url(r'^/combine_decryptions$', combine_decryptions),
    url(r'^/release_result$', release_result),
    
    # casting a ballot before we know who the voter is
    url(r'^/cast$', one_election_cast),
    url(r'^/cast_confirm$', one_election_cast_confirm),
    url(r'^/password_voter_login$', password_voter_login),
    url(r'^/cast_done$', one_election_cast_done),
    
    # post audited ballot
    url(r'^/post-audited-ballot', post_audited_ballot),
    
    # managing voters
    url(r'^/voters/$', voter_list),
    url(r'^/voters/upload$', voters_upload),
    url(r'^/voters/upload-cancel$', voters_upload_cancel),
    url(r'^/voters/list$', voters_list_pretty),
    url(r'^/voters/eligibility$', voters_eligibility),
    url(r'^/voters/email$', voters_email),
    url(r'^/voters/(?P<voter_uuid>[^/]+)$', one_voter),
    url(r'^/voters/(?P<voter_uuid>[^/]+)/delete$', voter_delete),
    
    # ballots
    url(r'^/ballots/$', ballot_list),
    url(r'^/ballots/(?P<voter_uuid>[^/]+)/all$', voter_votes),
    url(r'^/ballots/(?P<voter_uuid>[^/]+)/last$', voter_last_vote),

]
