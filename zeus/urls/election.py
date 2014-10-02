from django.conf.urls.defaults import *
from django.conf import settings

from zeus.urls.trustee import election_patterns

election_patterns = patterns('zeus.views.election',

    url(r'^$', 'index', name="election_index"),
    url(r'^edit$', 'add_or_update', name='election_edit'),
    url(r'^json$', 'json_data', name='election_json_data'),
    url(r'^polls/', include('zeus.urls.poll')),
    url(r'^polls/(?P<poll_uuid>[^/]+)$', 'index', name="election_poll_index"),
    url(r'^trustees/', include('zeus.urls.trustee')),
    url(r'^trustees/list$', 'trustees_list', name='election_trustees_list'),
    url(r'^trustees/(?P<trustee_uuid>[^/]+)/sendurl$', 'trustee_send_url',
        name='election_trustee_send_url'),
    url(r'^trustees/(?P<trustee_uuid>[^/]+)/delete$', 'trustee_delete',
        name='election_trustee_delete'),
    url(r'^trustee/', include(election_patterns)),
    url(r'^freeze$', 'freeze', name="election_freeze"),
    url(r'^cancel$', 'cancel', name="election_cancel"),
    # superadmin url
    url(r'^endnow$', 'endnow', name="election_endnow"),
    url(r'^close$', 'close', name="election_close"),
    url(r'^start-mixing$', 'start_mixing', name="election_start_mixing"),
    url(r'^report$', 'report', name="election_report"),
    url(r'^email-voters$', 'voters_email', name="election_voters_email"),
    url(r'^results/(?P<shortname>.*)-(?P<language>.*)\.pdf$', 'results_file',
        name="election_pdf_results",
        kwargs={'ext': 'pdf'}),
    url(r'^results/(?P<shortname>.*)-(?P<language>.*)\.csv$', 'results_file',
        name="election_csv_results",
        kwargs={'ext': 'csv'}),
    url(r'^results/(?P<shortname>.*)-(?P<language>.*)\.zip$', 'results_file',
        name="election_zip_results",
        kwargs={'ext': 'zip'}),
    url(r'^report.html$', 'report',
        name="election_report",
        kwargs={'format': 'html'}),
    url(r'^stats$', 'public_stats',
        name="election_public_stats"),


    # adding trustees
    #(r'^/trustees/$', list_trustees),
    #(r'^/trustees/view$', list_trustees_view),
    #(r'^/trustees/delete$', delete_trustee),

    ## trustee pages
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/home$', trustee_home),
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/keygenerator$', trustee_keygenerator),
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/check-sk$', trustee_check_sk),
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-pk$', trustee_upload_pk),
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/decrypt-and-prove$', trustee_decrypt_and_prove),
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/download-ciphers$', trustee_download_ciphers),
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-decryption$', trustee_upload_decryption),
    #(r'^/trustees/(?P<trustee_uuid>[^/]+)/verify-key$', trustee_verify_key),

    ## election voting-process actions
    #(r'^/view$', one_election_view),
    #(r'^/post-ecounting$', election_post_ecounting),
    #(r'^/result$', one_election_result),
    #(r'^/result_proof$', one_election_result_proof),
    #(r'^/zeus-proofs.zip$', election_zeus_proofs),
    #(r'^/result/results-(?P<name>[a-zA-Z0-9]+).(?P<ext>[a-z]{1,5})$', election_result_file),
    ## (r'^/bboard$', one_election_bboard),
    #(r'^/audited-ballots/$', one_election_audited_ballots),

    ## get randomness
    #(r'^/get-randomness$', get_randomness),

    ## construct election
    #(r'^/candidates$', one_election_candidates),
    #(r'^/questions$', one_election_questions),
    #(r'^/endnow$', one_election_force_end),

    ## computing tally
    #(r'^/compute_tally$', one_election_compute_tally),
    #(r'^/cancel$', one_election_cancel),
    #(r'^/set-completed', one_election_set_completed),
    #(r'^/report\.(?P<format>[a-z]+)$', election_report),
    #(r'^/mix/(?P<mix_key>.*)$', election_remote_mix),
    #(r'^/remove_last_mix$', election_remove_last_mix),
    #(r'^/stop-mixing$', election_stop_mixing),
    #(r'^/combine_decryptions$', combine_decryptions),

    ## casting a ballot before we know who the voter is
    #(r'^/cast$', one_election_cast),
    #(r'^/l/(?P<voter_uuid>.*)/(?P<voter_secret>.*)$', voter_quick_login),
    #(r'^/cast_done$', one_election_cast_done),
    #(r'^/s/(?P<fingerprint>.*)$', one_election_download_signature),

    ## post audited ballot
    #(r'^/post-audited-ballot', post_audited_ballot),

    ## ballots
    #(r'^/ballots/(?P<voter_uuid>[^/]+)/all$', voter_votes),
    #(r'^/ballots/(?P<voter_uuid>[^/]+)/last$', voter_last_vote),

    #(r'^/polls/', include('zeus.urls.election_poll')),
)

urlpatterns = patterns('zeus.views.election',
    url(r'^new$', 'add_or_update', name='election_create'),
    url(r'^(?P<election_uuid>[^/]+)/', include(election_patterns)),

    url(r'^testcookie$', 'test_cookie', name='test_cookie'),
    url(r'^testcookie_2$', 'test_cookie_2', name='test_cookie_2'),
    url(r'^nocookies$', 'nocookies', name='nocookies'),

)
