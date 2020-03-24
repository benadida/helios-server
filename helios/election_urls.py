"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls import url

from helios import views
from helios import election_url_names as names

urlpatterns = [
    # election data that is cryptographically verified
    url(r'^$', views.one_election, name=names.ELECTION_HOME),

    # metadata that need not be verified
    url(r'^/meta$', views.one_election_meta, name=names.ELECTION_META),
    
    # edit election params
    url(r'^/edit$', views.one_election_edit, name=names.ELECTION_EDIT),
    url(r'^/schedule$', views.one_election_schedule, name=names.ELECTION_SCHEDULE),
    url(r'^/extend$', views.one_election_extend, name=names.ELECTION_EXTEND),
    url(r'^/archive$', views.one_election_archive, name=names.ELECTION_ARCHIVE),
    url(r'^/copy$', views.one_election_copy, name=names.ELECTION_COPY),

    # badge
    url(r'^/badge$', views.election_badge, name=names.ELECTION_BADGE),

    # adding trustees
    url(r'^/trustees/$', views.list_trustees, name=names.ELECTION_TRUSTEES_HOME),
    url(r'^/trustees/view$', views.list_trustees_view, name=names.ELECTION_TRUSTEES_VIEW),
    url(r'^/trustees/new$', views.new_trustee, name=names.ELECTION_TRUSTEES_NEW),
    url(r'^/trustees/add-helios$', views.new_trustee_helios, name=names.ELECTION_TRUSTEES_ADD_HELIOS),
    url(r'^/trustees/delete$', views.delete_trustee, name=names.ELECTION_TRUSTEES_DELETE),
    
    # trustee pages
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/home$',
        views.trustee_home, name=names.ELECTION_TRUSTEE_HOME),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/sendurl$',
        views.trustee_send_url, name=names.ELECTION_TRUSTEE_SEND_URL),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/keygenerator$',
        views.trustee_keygenerator, name=names.ELECTION_TRUSTEE_KEY_GENERATOR),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/check-sk$',
        views.trustee_check_sk, name=names.ELECTION_TRUSTEE_CHECK_SK),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/upoad-pk$',
        views.trustee_upload_pk, name=names.ELECTION_TRUSTEE_UPLOAD_PK),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/decrypt-and-prove$',
        views.trustee_decrypt_and_prove, name=names.ELECTION_TRUSTEE_DECRYPT_AND_PROVE),
    url(r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-decryption$',
        views.trustee_upload_decryption, name=names.ELECTION_TRUSTEE_UPLOAD_DECRYPTION),
    
    # election voting-process actions
    url(r'^/view$', views.one_election_view, name=names.ELECTION_VIEW),
    url(r'^/result$', views.one_election_result, name=names.ELECTION_RESULT),
    url(r'^/result_proof$', views.one_election_result_proof, name=names.ELECTION_RESULT_PROOF),
    # url(r'^/bboard$', views.one_election_bboard, name=names.ELECTION_BBOARD),
    url(r'^/audited-ballots/$', views.one_election_audited_ballots, name=names.ELECTION_AUDITED_BALLOTS),

    # get randomness
    url(r'^/get-randomness$', views.get_randomness, name=names.ELECTION_GET_RANDOMNESS),

    # server-side encryption
    url(r'^/encrypt-ballot$', views.encrypt_ballot, name=names.ELECTION_ENCRYPT_BALLOT),

    # construct election
    url(r'^/questions$', views.one_election_questions, name=names.ELECTION_QUESTIONS),
    url(r'^/set_reg$', views.one_election_set_reg, name=names.ELECTION_SET_REG),
    url(r'^/set_featured$', views.one_election_set_featured, name=names.ELECTION_SET_FEATURED),
    url(r'^/save_questions$', views.one_election_save_questions, name=names.ELECTION_SAVE_QUESTIONS),
    url(r'^/register$', views.one_election_register, name=names.ELECTION_REGISTER),
    url(r'^/freeze$', views.one_election_freeze, name=names.ELECTION_FREEZE), # includes freeze_2 as POST target
    
    # computing tally
    url(r'^/compute_tally$', views.one_election_compute_tally, name=names.ELECTION_COMPUTE_TALLY),
    url(r'^/combine_decryptions$', views.combine_decryptions, name=names.ELECTION_COMBINE_DECRYPTIONS),
    url(r'^/release_result$', views.release_result, name=names.ELECTION_RELEASE_RESULT),
    
    # casting a ballot before we know who the voter is
    url(r'^/cast$', views.one_election_cast, name=names.ELECTION_CAST),
    url(r'^/cast_confirm$', views.one_election_cast_confirm, name=names.ELECTION_CAST_CONFIRM),
    url(r'^/password_voter_login$', views.password_voter_login, name=names.ELECTION_PASSWORD_VOTER_LOGIN),
    url(r'^/cast_done$', views.one_election_cast_done, name=names.ELECTION_CAST_DONE),
    
    # post audited ballot
    url(r'^/post-audited-ballot', views.post_audited_ballot, name=names.ELECTION_POST_AUDITED_BALLOT),
    
    # managing voters
    url(r'^/voters/$', views.voter_list, name=names.ELECTION_VOTERS_LIST),
    url(r'^/voters/upload$', views.voters_upload, name=names.ELECTION_VOTERS_UPLOAD),
    url(r'^/voters/upload-cancel$', views.voters_upload_cancel, name=names.ELECTION_VOTERS_UPLOAD_CANCEL),
    url(r'^/voters/list$', views.voters_list_pretty, name=names.ELECTION_VOTERS_LIST_PRETTY),
    url(r'^/voters/eligibility$', views.voters_eligibility, name=names.ELECTION_VOTERS_ELIGIBILITY),
    url(r'^/voters/email$', views.voters_email, name=names.ELECTION_VOTERS_EMAIL),
    url(r'^/voters/(?P<voter_uuid>[^/]+)$', views.one_voter, name=names.ELECTION_VOTER),
    url(r'^/voters/(?P<voter_uuid>[^/]+)/delete$', views.voter_delete, name=names.ELECTION_VOTER_DELETE),
    
    # ballots
    url(r'^/ballots/$', views.ballot_list, name=names.ELECTION_BALLOTS_LIST),
    url(r'^/ballots/(?P<voter_uuid>[^/]+)/all$', views.voter_votes, name=names.ELECTION_BALLOTS_VOTER),
    url(r'^/ballots/(?P<voter_uuid>[^/]+)/last$', views.voter_last_vote, name=names.ELECTION_BALLOTS_VOTER_LAST),

]
