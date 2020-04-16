"""
Glue some events together 
"""

import helios.signals
import helios.views
from helios.view_utils import render_template_raw


def vote_cast_send_message(user, voter, election, cast_vote, **kwargs):
    ## FIXME: this doesn't work for voters that are not also users
    # prepare the message
    subject_template = 'email/cast_vote_subject.txt'
    body_template = 'email/cast_vote_body.txt'

    extra_vars = {
        'election': election,
        'voter': voter,
        'cast_vote': cast_vote,
        'cast_vote_url': helios.views.get_castvote_url(cast_vote),
        'custom_subject': "%s - vote cast" % election.name
    }
    subject = render_template_raw(None, subject_template, extra_vars)
    body = render_template_raw(None, body_template, extra_vars)

    # send it via the notification system associated with the auth system
    user.send_message(subject, body)


def election_tallied(election, **kwargs):
    pass


def glue():
    helios.signals.vote_cast.connect(vote_cast_send_message)
    helios.signals.election_tallied.connect(election_tallied)
