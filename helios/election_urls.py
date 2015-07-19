"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls import *

from helios.views import *

urlpatterns = patterns('',
  # election data that is cryptographically verified
  (r'^$', one_election),

  # metadata that need not be verified
  (r'^/meta$', one_election_meta),

  # manage election
  (r'^/admin$', one_election_admin),
  (r'^/edit$', one_election_edit),
  (r'^/schedule$', one_election_schedule),
  (r'^/archive$', one_election_archive),

  # badge
  (r'^/badge$', election_badge),

  # adding trustees
  (r'^/trustees/$', trustees_list),
  (r'^/trustees/view$', trustees_list_view),
  (r'^/trustees/create$', trustees_create),
  (r'^/trustees/create-helios$', trustees_create_helios),
  (r'^/trustees/delete$', trustees_delete),
  (r'^/trustees/freeze$', trustees_freeze),

  # trustee pages
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/home$', trustee_home),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/sendurl$', trustee_send_url),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/keygenerator$', trustee_keygenerator),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/keygenerator-threshold$', trustee_keygenerator_threshold),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/check-sk$', trustee_check_sk),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-pk$', trustee_upload_pk),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/decrypt-and-prove$', trustee_decrypt_and_prove),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-decryption$', trustee_upload_decryption),
  (r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-encrypted-shares$', trustee_upload_encrypted_shares),

  # election voting-process actions
  (r'^/view$', one_election_view),
  (r'^/result$', one_election_result),
  (r'^/result-proof$', one_election_result_proof),
  (r'^/audited-ballots/$', one_election_audited_ballots),

  # server-side encryption
  (r'^/encrypt-ballot$', encrypt_ballot),

  # construct election
  (r'^/questions$', one_election_questions),
  (r'^/set-featured$', one_election_set_featured),
  (r'^/save-questions$', one_election_save_questions),
  (r'^/register$', one_election_register),
  # includes freeze_2 as POST target
  (r'^/freeze$', one_election_freeze),

  # computing tally
  (r'^/compute-tally$', one_election_compute_tally),
  (r'^/combine-decryptions$', combine_decryptions),
  (r'^/release-result$', release_result),

  # casting a ballot before we know who the voter is
  (r'^/cast$', one_election_cast),
  (r'^/cast-confirm$', one_election_cast_confirm),
  (r'^/password-voter-login$', password_voter_login),
  (r'^/cast-done$', one_election_cast_done),

  # post audited ballot
  (r'^/post-audited-ballot', post_audited_ballot),

  # managing voters
  (r'^/voters/$', voter_list),
  (r'^/voters/upload$', voters_upload),
  (r'^/voters/upload-cancel$', voters_upload_cancel),
  (r'^/voters/list$', voters_list_pretty),
  (r'^/voters/eligibility$', voters_eligibility),
  (r'^/voters/email$', voters_email),
  (r'^/voters/(?P<voter_uuid>[^/]+)$', one_voter),
  (r'^/voters/(?P<voter_uuid>[^/]+)/delete$', voter_delete),

  # ballots
  (r'^/ballots/$', ballot_list),
  (r'^/ballots/(?P<voter_uuid>[^/]+)/all$', voter_votes),
  (r'^/ballots/(?P<voter_uuid>[^/]+)/last$', voter_last_vote),
)
