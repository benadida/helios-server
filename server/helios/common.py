import urllib

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404

from helios.models import Election, Voter, CastVote, Trustee
from helios.security import election_view, user_can_admin_election, user_can_feature_election, get_voter
from helios.view_utils import render_template, return_json
from helios_auth import views as auth_views
from helios_auth.models import AuthenticationExpired
from helios_auth.security import get_user


def get_election_url(election):
    return settings.URL_HOST + reverse(election_shortcut, args=[election.short_name])


def election_shortcut(request, election_short_name):
    election = Election.get_by_short_name(election_short_name)
    if election:
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
    else:
        raise Http404


@election_view()
def one_election_view(request, election):
    user = get_user(request)
    admin_p = user_can_admin_election(user, election)
    can_feature_p = user_can_feature_election(user, election)

    notregistered = False
    eligible_p = True

    election_url = get_election_url(election)
    election_badge_url = get_election_badge_url(election)
    status_update_message = None

    vote_url = "%s/booth/vote.html?%s" % (
    settings.SECURE_URL_HOST, urllib.parse.urlencode({'election_url': reverse(one_election, args=[election.uuid])}))

    test_cookie_url = "%s?%s" % (reverse(test_cookie), urllib.parse.urlencode({'continue_url': vote_url}))

    if user:
        voter = Voter.get_by_election_and_user(election, user)

        if not voter:
            try:
                eligible_p = _check_eligibility(election, user)
            except AuthenticationExpired:
                return user_reauth(request, user)
            notregistered = True
    else:
        voter = get_voter(request, user, election)

    if voter:
        # cast any votes?
        votes = CastVote.get_by_voter(voter)
    else:
        votes = None

    # status update message?
    if election.openreg:
        if election.voting_has_started:
            status_update_message = "Vote in %s" % election.name
        else:
            status_update_message = "Register to vote in %s" % election.name

    # result!
    if election.result:
        status_update_message = "Results are in for %s" % election.name

    trustees = Trustee.get_by_election(election)

    # should we show the result?
    show_result = election.result_released_at or (election.result and admin_p)

    return render_template(request, 'election_view',
                           {'election': election, 'trustees': trustees, 'admin_p': admin_p, 'user': user,
                            'voter': voter, 'votes': votes, 'notregistered': notregistered, 'eligible_p': eligible_p,
                            'can_feature_p': can_feature_p, 'election_url': election_url,
                            'vote_url': vote_url, 'election_badge_url': election_badge_url,
                            'show_result': show_result,
                            'test_cookie_url': test_cookie_url})


def get_election_badge_url(election):
  return settings.URL_HOST + reverse(election_badge, args=[election.uuid])


@election_view()
@return_json
def one_election(request, election):
  if not election:
    raise Http404
  return election.toJSONDict(complete=True)


def test_cookie(request):
  continue_url = request.GET['continue_url']
  request.session.set_test_cookie()
  next_url = "%s?%s" % (reverse(test_cookie_2), urllib.parse.urlencode({'continue_url': continue_url}))
  return HttpResponseRedirect(settings.SECURE_URL_HOST + next_url)


def _check_eligibility(election, user):
  # prevent password-users from signing up willy-nilly for other elections, doesn't make sense
  if user.user_type == 'password':
    return False

  return election.user_eligible_p(user)


def user_reauth(request, user):
  # FIXME: should we be wary of infinite redirects here, and
  # add a parameter to prevent it? Maybe.
  login_url = "%s%s?%s" % (settings.SECURE_URL_HOST,
                           reverse(auth_views.start, args=[user.user_type]),
                           urllib.parse.urlencode({'return_url':
                                               request.get_full_path()}))
  return HttpResponseRedirect(login_url)


@election_view()
def election_badge(request, election):
  election_url = get_election_url(election)
  params = {'election': election, 'election_url': election_url}
  for option_name in ['show_title', 'show_vote_link']:
    params[option_name] = (request.GET.get(option_name, '1') == '1')
  return render_template(request, "election_badge", params)


def test_cookie_2(request):
  continue_url = request.GET['continue_url']

  if not request.session.test_cookie_worked():
    return HttpResponseRedirect(settings.SECURE_URL_HOST + ("%s?%s" % (reverse(nocookies), urllib.parse.urlencode({'continue_url': continue_url}))))

  request.session.delete_test_cookie()
  return HttpResponseRedirect(continue_url)


def nocookies(request):
  retest_url = "%s?%s" % (reverse(test_cookie), urllib.parse.urlencode({'continue_url' : request.GET['continue_url']}))
  return render_template(request, 'nocookies', {'retest_url': retest_url})
