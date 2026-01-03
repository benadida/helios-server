"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.urls import path, re_path

from helios import views
from helios import election_url_names as names

urlpatterns = [
    # election data that is cryptographically verified
    path('', views.one_election, name=names.ELECTION_HOME),

    # metadata that need not be verified
    path('/meta', views.one_election_meta, name=names.ELECTION_META),
    
    # edit election params
    path('/edit', views.one_election_edit, name=names.ELECTION_EDIT),
    path('/schedule', views.one_election_schedule, name=names.ELECTION_SCHEDULE),
    path('/extend', views.one_election_extend, name=names.ELECTION_EXTEND),
    path('/archive', views.one_election_archive, name=names.ELECTION_ARCHIVE),
    path('/copy', views.one_election_copy, name=names.ELECTION_COPY),

    # badge
    path('/badge', views.election_badge, name=names.ELECTION_BADGE),

    # adding trustees
    path('/trustees/', views.list_trustees, name=names.ELECTION_TRUSTEES_HOME),
    path('/trustees/view', views.list_trustees_view, name=names.ELECTION_TRUSTEES_VIEW),
    path('/trustees/new', views.new_trustee, name=names.ELECTION_TRUSTEES_NEW),
    path('/trustees/add-helios', views.new_trustee_helios, name=names.ELECTION_TRUSTEES_ADD_HELIOS),
    path('/trustees/delete', views.delete_trustee, name=names.ELECTION_TRUSTEES_DELETE),

    # managing administrators
    path('/admins/', views.election_admin_list, name=names.ELECTION_ADMINS_LIST),
    path('/admins/add', views.election_admin_add, name=names.ELECTION_ADMINS_ADD),
    path('/admins/remove', views.election_admin_remove, name=names.ELECTION_ADMINS_REMOVE),
    
    # trustee pages
    path('/trustees/<str:trustee_uuid>/home',
        views.trustee_home, name=names.ELECTION_TRUSTEE_HOME),
    path('/trustees/<str:trustee_uuid>/sendurl',
        views.trustee_send_url, name=names.ELECTION_TRUSTEE_SEND_URL),
    path('/trustees/<str:trustee_uuid>/keygenerator',
        views.trustee_keygenerator, name=names.ELECTION_TRUSTEE_KEY_GENERATOR),
    path('/trustees/<str:trustee_uuid>/check-sk',
        views.trustee_check_sk, name=names.ELECTION_TRUSTEE_CHECK_SK),
    path('/trustees/<str:trustee_uuid>/upoad-pk',
        views.trustee_upload_pk, name=names.ELECTION_TRUSTEE_UPLOAD_PK),
    path('/trustees/<str:trustee_uuid>/decrypt-and-prove',
        views.trustee_decrypt_and_prove, name=names.ELECTION_TRUSTEE_DECRYPT_AND_PROVE),
    path('/trustees/<str:trustee_uuid>/upload-decryption',
        views.trustee_upload_decryption, name=names.ELECTION_TRUSTEE_UPLOAD_DECRYPTION),
    
    # election voting-process actions
    path('/view', views.one_election_view, name=names.ELECTION_VIEW),
    path('/result', views.one_election_result, name=names.ELECTION_RESULT),
    path('/result_proof', views.one_election_result_proof, name=names.ELECTION_RESULT_PROOF),
    # url(r'^/bboard$', views.one_election_bboard, name=names.ELECTION_BBOARD),
    path('/audited-ballots/', views.one_election_audited_ballots, name=names.ELECTION_AUDITED_BALLOTS),

    # get randomness
    path('/get-randomness', views.get_randomness, name=names.ELECTION_GET_RANDOMNESS),

    # construct election
    path('/questions', views.one_election_questions, name=names.ELECTION_QUESTIONS),
    path('/set_reg', views.one_election_set_reg, name=names.ELECTION_SET_REG),
    path('/set_featured', views.one_election_set_featured, name=names.ELECTION_SET_FEATURED),
    path('/save_questions', views.one_election_save_questions, name=names.ELECTION_SAVE_QUESTIONS),
    path('/register', views.one_election_register, name=names.ELECTION_REGISTER),
    path('/freeze', views.one_election_freeze, name=names.ELECTION_FREEZE), # includes freeze_2 as POST target
    
    # computing tally
    path('/compute_tally', views.one_election_compute_tally, name=names.ELECTION_COMPUTE_TALLY),
    path('/combine_decryptions', views.combine_decryptions, name=names.ELECTION_COMBINE_DECRYPTIONS),
    path('/release_result', views.release_result, name=names.ELECTION_RELEASE_RESULT),
    
    # casting a ballot before we know who the voter is
    path('/cast', views.one_election_cast, name=names.ELECTION_CAST),
    path('/cast_confirm', views.one_election_cast_confirm, name=names.ELECTION_CAST_CONFIRM),
    path('/password_voter_login', views.password_voter_login, name=names.ELECTION_PASSWORD_VOTER_LOGIN),
    path('/cast_done', views.one_election_cast_done, name=names.ELECTION_CAST_DONE),
    
    # post audited ballot
    re_path(r'^/post-audited-ballot', views.post_audited_ballot, name=names.ELECTION_POST_AUDITED_BALLOT),
    
    # managing voters
    path('/voters/', views.voter_list, name=names.ELECTION_VOTERS_LIST),
    path('/voters/upload', views.voters_upload, name=names.ELECTION_VOTERS_UPLOAD),
    path('/voters/upload-cancel', views.voters_upload_cancel, name=names.ELECTION_VOTERS_UPLOAD_CANCEL),
    path('/voters/list', views.voters_list_pretty, name=names.ELECTION_VOTERS_LIST_PRETTY),
    path('/voters/download-csv', views.voters_download_csv, name='election@voters@download-csv'),
    path('/voters/eligibility', views.voters_eligibility, name=names.ELECTION_VOTERS_ELIGIBILITY),
    path('/voters/email', views.voters_email, name=names.ELECTION_VOTERS_EMAIL),
    path('/voters/clear', views.voters_clear, name=names.ELECTION_VOTERS_CLEAR),
    path('/voters/<str:voter_uuid>', views.one_voter, name=names.ELECTION_VOTER),
    path('/voters/<str:voter_uuid>/delete', views.voter_delete, name=names.ELECTION_VOTER_DELETE),
    
    # ballots
    path('/ballots/', views.ballot_list, name=names.ELECTION_BALLOTS_LIST),
    path('/ballots/<str:voter_uuid>/all', views.voter_votes, name=names.ELECTION_BALLOTS_VOTER),
    path('/ballots/<str:voter_uuid>/last', views.voter_last_vote, name=names.ELECTION_BALLOTS_VOTER_LAST),

]
