import os
import csv
import json
from collections import OrderedDict

from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.db import connection
from django.db.models.query import EmptyQuerySet
from django.core.context_processors import csrf
from django.core.validators import validate_email
from django.utils.html import mark_safe, escape
from django import forms

from zeus.forms import ElectionForm
from zeus import auth
from zeus.forms import PollForm, PollFormSet, EmailVotersForm
from zeus.utils import *
from zeus.views.utils import *
from zeus import tasks

from django.utils.encoding import smart_unicode
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.exceptions import PermissionDenied
from django.forms.models import modelformset_factory
from django.template.loader import render_to_string
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from helios.view_utils import render_template
from helios.models import Election, Poll, Voter, VoterFile, CastVote, \
    AuditedBallot
from helios import datatypes
from helios import exceptions
from helios.crypto import utils as crypto_utils
from helios.crypto import electionalgs
from helios.utils import force_utf8


@auth.election_admin_required
def list(request, election):
    polls = election.polls.filter()
    extra = int(request.GET.get('extra', 1))
    polls_formset = modelformset_factory(Poll, PollForm, extra=extra,
                                         max_num=100, formset=PollFormSet,
                                         can_delete=False)
    add_polls = Poll.objects.none()
    form = polls_formset(queryset=add_polls)
    context = {'polls': polls, 'election': election, 'form': form}
    set_menu('polls', context)
    return render_template(request, "election_polls_list", context)


@auth.election_admin_required
@auth.requires_election_features('can_rename_poll')
@transaction.commit_on_success
@require_http_methods(["POST"])
def rename(request, election, poll):
    newname = request.POST.get('name', '').strip()
    if newname:
        oldname = poll.name
        poll.name = newname
        poll.save()
        poll.logger.info("Renamed from %s to %s", oldname, newname)
    url = election_reverse(election, 'polls_list')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_election_features('can_add_poll')
@require_http_methods(["POST", "GET"])
def add(request, election, poll=None):
    if request.method == "GET":
        url = election_reverse(election, 'polls_list')
        return HttpResponseRedirect(url)
    extra = int(request.GET.get('extra', 2))
    polls_formset = modelformset_factory(Poll, PollForm, extra=extra,
                                         max_num=100, formset=PollFormSet,
                                         can_delete=False)
    polls = Poll.objects.none()
    form = polls_formset(request.POST, queryset=polls, election=election)
    if form.is_valid():
        with transaction.commit_on_success():
            polls = form.save(election)
            for poll in polls:
                poll.logger.info("Poll created")
    else:
        polls = Poll.objects.filter(election=election)
        context = {'polls': polls, 'election': election, 'form': form}
        set_menu('polls', context)
        return render_template(request, "election_polls_list", context)
    url = election_reverse(election, 'polls_list')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@require_http_methods(["POST"])
def remove(request, election, poll):
    poll.delete()
    poll.logger.info("Poll deleted")
    return HttpResponseRedirect(election_reverse(election, 'polls_list'))


@auth.election_admin_required
@auth.requires_poll_features('can_manage_questions')
@require_http_methods(["POST", "GET"])
def questions_manage(request, election, poll):
    module = poll.get_module()
    return module.questions_update_view(request, election, poll)


@auth.election_view()
@require_http_methods(["GET"])
def questions(request, election, poll):
    module = poll.get_module()
    if request.zeususer.is_admin:
        if not module.questions_set() and poll.feature_can_manage_questions:
            url = poll_reverse(poll, 'questions_manage')
            return HttpResponseRedirect(url)

    context = {
        'election': election,
        'poll': poll,
        'questions': questions,
        'module': poll.get_module()
    }
    set_menu('questions', context)
    tpl = getattr(module, 'questions_list_template', 'election_poll_questions')
    return render_template(request, tpl, context)


@auth.election_admin_required
@require_http_methods(["GET"])
def voters_list(request, election, poll):
    # for django pagination support
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    q_param = request.GET.get('q', '')
    order_type = request.GET.get('order_type', None)
    default_voters_per_page = getattr(settings, 'ELECTION_VOTERS_PER_PAGE', 100)
    voters_per_page = request.GET.get('limit', default_voters_per_page)
    try:
        voters_per_page = int(voters_per_page)
    except:
        voters_per_page = default_voters_per_page
    voter_table_header = OrderedDict([
        ('voter_login_id', _('Registration ID')),
        ('voter_email', _('Email')),
        ('voter_surname', _('Surname')),
        ('voter_name', _('Given name')),
        ('voter_fathername', _('Middle name')),
        ('voter_mobile', _('Mobile phone')),
        ('cast_votes__id', _('Has voted')),
        ('last_booth_invitation_send_at', _('Booth invitation sent at')),
        ('last_visit', _('Last visit')),
        ('actions', _('Actions'))
        ])

    order_by = 'voter_login_id'
    order_by = request.GET.get('order', 'voter_login_id')
    if not order_by in voter_table_header.keys(): 
        order_by = 'voter_login_id'

    validate_hash = request.GET.get('vote_hash', "").strip()
    hash_invalid = None
    hash_valid = None
    
    if (order_type == 'asc') or (order_type == None) :
        voters = Voter.objects.filter(poll=poll).order_by(order_by)
    else:
        order_by = '-%s' % order_by
        voters = Voter.objects.filter(poll=poll).order_by(order_by)
    
    voters = utils.get_filtered_voters(q_param, voters)
    voters_count = Voter.objects.filter(poll=poll).count()
    voted_count = poll.voters_cast_count()

    context = {
        'election': election,
        'poll': poll,
        'limit': limit,
        'page': page,
        'voters': voters,
        'voters_count': voters_count,
        'voted_count': voted_count,
        'q': q_param,
        'voters_per_page': voters_per_page,
        'voter_table_header': voter_table_header.iteritems(),
    }
    set_menu('voters', context)
    return render_template(request, 'election_poll_voters_list', context)


@auth.election_admin_required
@auth.requires_poll_features('can_clear_voters')
@transaction.commit_on_success
@require_http_methods(["POST"])
def voters_clear(request, election, poll):
    for voter in poll.voters.all():
        if not voter.cast_votes.count():
            voter.delete()
        poll.logger.info("Poll voters cleared")
    url = poll_reverse(poll, 'voters')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_poll_features('can_add_voter')
@require_http_methods(["POST", "GET"])
def voters_upload(request, election, poll):
    common_context = {
        'election': election,
        'poll': poll
    }
    set_menu('voters', common_context)
    if request.method == "POST":
        if bool(request.POST.get('confirm_p', 0)):
            # launch the background task to parse that file
            voter_file_id = request.session.get('voter_file_id', None)
            if not voter_file_id:
                messages.error(request, "Invalid voter file id")
                url = poll_reverse(poll, 'voters')
                return HttpResponseRedirect(url)
            try:
                voter_file = VoterFile.objects.get(pk=voter_file_id)
                try:
                    voter_file.process()
                except (exceptions.VoterLimitReached, \
                    exceptions.DuplicateVoterID) as e:
                    messages.error(request, e.message)
                    voter_file.delete()
                    url = poll_reverse(poll, 'voters')
                    return HttpResponseRedirect(url)

                poll.logger.info("Processing voters upload")
            except VoterFile.DoesNotExist:
                pass
            except KeyError:
                pass
            if 'voter_file_id' in request.session:
                del request.session['voter_file_id']
            url = poll_reverse(poll, 'voters')
            return HttpResponseRedirect(url)
        else:
            if 'voter_file_id' in request.session:
                del request.session['voter_file_id']
            # we need to confirm
            voters = []
            error = None
            invalid_emails = []

            def _email_validate(eml, line):
                try:
                    validate_email(eml)
                except ValidationError:
                    invalid_emails.append((eml, line))
                return True

            if request.FILES.has_key('voters_file'):
                voters_file = request.FILES['voters_file']
                voter_file_obj = poll.add_voters_file(voters_file)

                # import the first few lines to check
                invalid_emails = []
                try:
                    voters = [v for v in voter_file_obj.itervoters(
                                            email_validator=_email_validate)]
                except ValidationError, e:
                    if hasattr(e, 'messages') and e.messages:
                        error = "".join(e.messages)
                    else:
                        error = "error."
                except Exception, e:
                    error = str(e)

                if len(invalid_emails):
                    error = _("Enter a valid email address. "
                              "<br />")
                    for email, line in invalid_emails:
                        error += "<br />" + "line %d: %s " % (line,
                            escape(email))

                    error = mark_safe(error)
            else:
                error = _("No file uploaded")
            if not error:
                request.session['voter_file_id'] = voter_file_obj.id
            count = len(voters)
            context = common_context
            context.update({
                'voters': voters,
                'count': count,
                'error': error
            })
            return render_template(request,
                                   'election_poll_voters_upload_confirm',
                                   context)
    else:
        if 'voter_file_id' in request.session:
            del request.session['voter_file_id']
        return render_template(request,
                               'election_poll_voters_upload',
                               common_context)


@auth.election_admin_required
@require_http_methods(["POST"])
def voters_upload_cancel(request, election, poll):
    voter_file_id = request.session.get('voter_file_id', None)
    if voter_file_id:
        vf = VoterFile.objects.get(id = voter_file_id)
        vf.delete()
    if 'voter_file_id' in request.session:
        del request.session['voter_file_id']

    url = poll_reverse(poll, 'voters_upload')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@require_http_methods(["POST", "GET"])
def voters_email(request, election, poll=None, voter_uuid=None):
    user = request.admin

    TEMPLATES = [
        ('vote', _('Time to Vote')),
        ('info', _('Additional Info')),
    ]


    default_template = 'vote'

    if not election.any_poll_feature_can_send_voter_mail:
        raise PermissionDenied('34')

    if not election.any_poll_feature_can_send_voter_booth_invitation:
        TEMPLATES.pop(0)
        default_template = 'info'

    if election.voting_extended_until and not election.voting_ended_at:
        TEMPLATES.append(('extension', _('Voting end date extended')))

    template = request.REQUEST.get('template', default_template)

    if not template in [t[0] for t in TEMPLATES]:
        raise Exception("bad template")

    polls = [poll]
    if not poll:
        polls = election.polls.all()

    voter = None
    if voter_uuid:
        try:
            if poll:
                voter = get_object_or_404(Voter, uuid=voter_uuid, poll=poll)
            else:
                voter = get_object_or_404(Voter, uuid=voter_uuid,
                                          election=election)
        except Voter.DoesNotExist:
            raise PermissionDenied('35')
        if not voter:
            url = election_reverse(election, 'index')
            return HttpResponseRedirect(url)

    election_url = election.get_absolute_url()

    default_subject = render_to_string(
        'email/%s_subject.txt' % template, {
            'custom_subject': "&lt;SUBJECT&gt;"
        })

    default_body = render_to_string(
        'email/%s_body.txt' % template, {
            'election' : election,
            'election_url' : election_url,
            'custom_subject' : default_subject,
            'custom_message': '&lt;BODY&gt;',
            'voter': {
                'vote_hash' : '<SMART_TRACKER>',
                'name': '<VOTER_NAME>',
                'voter_name': '<VOTER_NAME>',
                'voter_surname': '<VOTER_SURNAME>',
                'voter_login_id': '<VOTER_LOGIN_ID>',
                'voter_password': '<VOTER_PASSWORD>',
                'audit_passwords': '1',
                'get_audit_passwords': ['pass1', 'pass2', '...'],
                'get_quick_login_url': '<VOTER_LOGIN_URL>',
                'poll': poll,
                'election' : election}
            })

    if request.method == "GET":
        email_form = EmailVotersForm()
        email_form.fields['subject'].initial = dict(TEMPLATES)[template]
        if voter:
            email_form.fields['send_to'].widget = \
                email_form.fields['send_to'].hidden_widget()
    else:
        email_form = EmailVotersForm(request.POST)
        if email_form.is_valid():
            # the client knows to submit only once with a specific voter_id
            voter_constraints_include = None
            voter_constraints_exclude = None
            update_booth_invitation_date = False
            if template == 'vote':
                update_booth_invitation_date = True

            if voter:
                voter_constraints_include = {'uuid': voter.uuid}

            # exclude those who have not voted
            if email_form.cleaned_data['send_to'] == 'voted':
                voter_constraints_exclude = {'vote_hash' : None}

            # include only those who have not voted
            if email_form.cleaned_data['send_to'] == 'not-voted':
                voter_constraints_include = {'vote_hash': None}

            for _poll in polls:
                if not _poll.feature_can_send_voter_mail:
                    continue

                if template == 'vote' and not \
                        _poll.feature_can_send_voter_booth_invitation:
                    continue

                subject_template = 'email/%s_subject.txt' % template
                body_template = 'email/%s_body.txt' % template
                extra_vars = {
                    'custom_subject' : email_form.cleaned_data['subject'],
                    'custom_message' : email_form.cleaned_data['body'],
                    'election_url' : election_url,
                }
                q_param = request.GET.get('q', None)
                task_kwargs = {
                    'subject_template': subject_template,
                    'body_template': body_template,
                    'extra_vars': extra_vars,
                    'voter_constraints_include': voter_constraints_include,
                    'voter_constraints_exclude': voter_constraints_exclude,
                    'update_date': True,
                    'update_booth_invitation_date': update_booth_invitation_date,
                    'q_param': q_param,
                }
                log_obj = election
                if poll:
                    log_obj = poll
                if voter:
                    log_obj.logger.info("Notifying single voter %s, [template: %s]",
                                     voter.voter_login_id, template)
                else:
                    log_obj.logger.info("Notifying voters, [template: %s]", template)
                tasks.voters_email.delay(_poll.pk, **task_kwargs)

            # this batch process is all async, so we can return a nice note
            messages.info(request, _("Email sending started"))
            url = election_reverse(election, 'polls_list')
            if poll:
                url = poll_reverse(poll, 'voters')
            if q_param:
                url += '?q=%s' % q_param
            return HttpResponseRedirect(url)

    context = {
        'email_form': email_form,
        'election': election,
        'poll': poll,
        'voter_o': voter,
        'default_subject': default_subject,
        'default_body': default_body,
        'template': template,
        'templates': TEMPLATES
    }
    set_menu('voters', context)
    if not poll:
        set_menu('polls', context)
    return render_template(request, "voters_email", context)


@auth.election_admin_required
@auth.requires_poll_features('can_delete_voter')
@require_http_methods(["POST"])
def voter_delete(request, election, poll, voter_uuid):
    voter = get_object_or_404(Voter, poll=poll, uuid=voter_uuid)
    if voter.voted:
        raise PermissionDenied('36')
    voter.delete()
    poll.logger.info("Poll voter '%s' removed", voter.voter_login_id)
    url = poll_reverse(poll, 'voters')
    return HttpResponseRedirect(url)


@auth.election_admin_required
@auth.requires_poll_features('can_exclude_voter')
@require_http_methods(["POST"])
def voter_exclude(request, election, poll, voter_uuid):
    voter = get_object_or_404(Voter, uuid=voter_uuid, poll=poll)
    if not voter.excluded_at:
        reason = request.POST.get('reason', '')
        poll.zeus.exclude_voter(voter.uuid, reason)
        poll.logger.info("Poll voter '%s' excluded", voter.voter_login_id)
    return HttpResponseRedirect(poll_reverse(poll, 'voters'))


@auth.election_admin_required
@require_http_methods(["GET"])
def voters_csv(request, election, poll, fname):
    response = HttpResponse(mimetype='text/csv')
    filename = smart_unicode("voters-%s.csv" % election.short_name)
    if fname:
        filename = fname
    response['Content-Dispotition'] = \
            'attachment; filename="%s.csv"' % filename
    poll.voters_to_csv(response)
    return response


@auth.election_view(check_access=False)
@require_http_methods(["GET"])
def voter_booth_login(request, election, poll, voter_uuid, voter_secret):
    voter = None
    try:
        voter = Voter.objects.get(poll=poll, uuid=voter_uuid)
        if voter.excluded_at:
            raise PermissionDenied('37')
    except Voter.DoesNotExist:
        raise PermissionDenied("Invalid election")

    if request.zeususer.is_authenticated() and (
            not request.zeususer.is_voter or \
                request.zeususer._user.pk != voter.pk):
        messages.error(request,
                        _("You need to logout from your current account "
                            "to access this view."))
        return HttpResponseRedirect(reverse('error', kwargs={'code': 403}))

    if voter.voter_password == unicode(voter_secret):
        user = auth.ZeusUser(voter)
        user.authenticate(request)
        poll.logger.info("Poll voter '%s' logged in", voter.voter_login_id)
        return HttpResponseRedirect(poll_reverse(poll, 'index'))
    raise PermissionDenied('38')


@auth.election_view(check_access=False)
@require_http_methods(["GET"])
def to_json(request, election, poll):
    data = poll.get_booth_dict()
    data['token'] = unicode(csrf(request)['csrf_token'])
    return HttpResponse(json.dumps(data, default=common_json_handler),
                        mimetype="application/json")


@auth.poll_voter_required
@auth.requires_poll_features('can_cast_vote')
@require_http_methods(["POST"])
def post_audited_ballot(request, election, poll):
    voter = request.voter
    raw_vote = request.POST['audited_ballot']
    encrypted_vote = crypto_utils.from_json(raw_vote)
    audit_request = crypto_utils.from_json(request.session['audit_request'])
    audit_password = request.session['audit_password']

    if not audit_password:
        raise Exception("Auditing with no password")

    # fill in the answers and randomness
    audit_request['answers'][0]['randomness'] = \
            encrypted_vote['answers'][0]['randomness']
    audit_request['answers'][0]['answer'] = \
            [encrypted_vote['answers'][0]['answer'][0]]
    encrypted_vote = electionalgs.EncryptedVote.fromJSONDict(audit_request)

    del request.session['audit_request']
    del request.session['audit_password']

    poll.cast_vote(voter, encrypted_vote, audit_password)
    poll.logger.info("Poll audit ballot cast")
    vote_pk = AuditedBallot.objects.filter(voter=voter).order_by('-pk')[0].pk

    return HttpResponse(json.dumps({'audit_id': vote_pk }),
                        content_type="application/json")


@auth.poll_voter_required
@auth.requires_poll_features('can_cast_vote')
@require_http_methods(["POST"])
def cast(request, election, poll):
    voter = request.voter
    encrypted_vote = request.POST['encrypted_vote']
    vote = datatypes.LDObject.fromDict(crypto_utils.from_json(encrypted_vote),
        type_hint='phoebus/EncryptedVote').wrapped_obj
    audit_password = request.POST.get('audit_password', None)

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT pg_advisory_lock(1)")
        with transaction.commit_on_success():
            cast_result = poll.cast_vote(voter, vote, audit_password)
            poll.logger.info("Poll cast")
    finally:
        cursor.execute("SELECT pg_advisory_unlock(1)")

    signature = {'signature': cast_result}

    if 'audit_request' in request.session:
        poll.logger.info("Poll cast audit request")
        del request.session['audit_request']
    else:
        poll.logger.info("Poll cast")

    if signature['signature'].startswith("AUDIT REQUEST"):
        request.session['audit_request'] = encrypted_vote
        request.session['audit_password'] = audit_password
        token = request.session.get('csrf_token')
        return HttpResponse('{"audit": 1, "token":"%s"}' % token,
                            mimetype="application/json")
    else:
        # notify user
        tasks.send_cast_vote_email.delay(poll.pk, voter.pk, signature)
        fingerprint = voter.cast_votes.filter()[0].fingerprint
        url = "%s%s?f=%s" % (settings.SECURE_URL_HOST, poll_reverse(poll,
                                                               'cast_done'),
                             fingerprint)

        return HttpResponse('{"cast_url": "%s"}' % url,
                            mimetype="application/json")


@auth.election_view(check_access=False)
@require_http_methods(["GET"])
def cast_done(request, election, poll):
    if request.zeususer.is_authenticated() and request.zeususer.is_voter:
        request.zeususer.logout(request)

    fingerprint = request.GET.get('f')
    if not request.GET.get('f', None):
        raise PermissionDenied('39')

    vote = get_object_or_404(CastVote, fingerprint=fingerprint)

    return render_template(request, 'election_poll_cast_done', {
                               'cast_vote': vote,
                               'election_uuid': election.uuid,
                               'poll_uuid': poll.uuid
    })


@auth.election_view(check_access=False)
@require_http_methods(["GET"])
def download_signature(request, election, poll, fingerprint):
    vote = CastVote.objects.get(voter__poll=poll, fingerprint=fingerprint)
    response = HttpResponse(content_type='application/binary')
    response['Content-Dispotition'] = 'attachment; filename=signature.txt'
    response.write(vote.signature['signature'])
    return response


@auth.election_view()
@require_http_methods(["GET"])
def audited_ballots(request, election, poll):
    vote_hash = request.GET.get('vote_hash', None)
    if vote_hash:
        b = get_object_or_404(AuditedBallot, poll=poll, vote_hash=vote_hash)
        b = AuditedBallot.objects.get(poll=poll,
                                      vote_hash=request.GET['vote_hash'])
        return HttpResponse(b.raw_vote, mimetype="text/plain")

    audited_ballots = AuditedBallot.objects.filter(is_request=False,
                                                   poll=poll)

    voter = None
    if request.zeususer.is_voter:
        voter = request.voter

    voter_audited_ballots = []
    if voter:
        voter_audited_ballots = AuditedBallot.objects.filter(poll=poll,
                                                             is_request=False,
                                                             voter=voter)
    context = {
        'election': election,
        'audited_ballots': audited_ballots,
        'voter_audited_ballots': voter_audited_ballots,
        'poll': poll,
        'per_page': 50
    }
    set_menu('audited_ballots', context)
    return render_template(request, 'election_poll_audited_ballots', context)


@auth.trustee_view
@auth.requires_poll_features('can_do_partial_decrypt')
@transaction.commit_on_success
@require_http_methods(["POST"])
def upload_decryption(request, election, poll, trustee):
    factors_and_proofs = crypto_utils.from_json(
        request.POST['factors_and_proofs'])

    # verify the decryption factors
    LD = datatypes.LDObject
    factors_data = factors_and_proofs['decryption_factors']
    factor = lambda fd: LD.fromDict(fd, type_hint='core/BigInteger').wrapped_obj
    factors = [[factor(f) for f in factors_data[0]]]

    proofs_data = factors_and_proofs['decryption_proofs']
    proof = lambda pd: LD.fromDict(pd, type_hint='legacy/EGZKProof').wrapped_obj
    proofs = [[proof(p) for p in proofs_data[0]]]
    poll.logger.info("Poll decryption uploaded")
    tasks.poll_add_trustee_factors.delay(poll.pk, trustee.pk, factors, proofs)

    return HttpResponse("SUCCESS")


@auth.election_view()
@auth.requires_poll_features('can_do_partial_decrypt')
@require_http_methods(["GET"])
def get_tally(request, election, poll):
    if not request.zeususer.is_trustee:
        raise PermissionDenied('40')

    params = poll.get_booth_dict()
    tally = poll.encrypted_tally.toJSONDict()

    return HttpResponse(json.dumps({
        'poll': params,
        'tally': tally}, default=common_json_handler),
        mimetype="application/json")


@auth.election_view()
@auth.requires_poll_features('compute_results_finished')
@require_http_methods(["GET"])
def results(request, election, poll):
    if not request.zeususer.is_admin and not poll.feature_public_results:
        raise PermissionDenied('41')

    context = {
        'poll': poll,
        'election': election
    }
    set_menu('results', context)
    return render_template(request, 'election_poll_results', context)


@auth.election_admin_required
@auth.requires_poll_features('compute_results_finished')
@require_http_methods(["GET"])
def results_file(request, election, poll, language, ext):
    lang = language
    name = ext
    el_module = poll.get_module()

    if not os.path.exists(el_module.get_poll_result_file_path('pdf', 'pdf',\
        lang)):
        if el_module.pdf_result:
            el_module.generate_result_docs((lang,lang))

    if not os.path.exists(el_module.get_poll_result_file_path('csv', 'csv',\
        lang)):
        if el_module.csv_result:
            el_module.generate_csv_file((lang, lang))

    if request.GET.get('gen', None):
        el_module.compute_results()

    fname = el_module.get_poll_result_file_path(name, ext, lang=lang)

    if not os.path.exists(fname):
        raise Http404

    if settings.USE_X_SENDFILE:
        response = HttpResponse()
        response['Content-Type'] = ''
        response['X-Sendfile'] = fname
        return response
    else:
        zip_data = file(fname, 'r')
        response = HttpResponse(zip_data.read(), mimetype='application/%s' % ext)
        zip_data.close()
        basename = os.path.basename(fname)
        response['Content-Dispotition'] = 'attachment; filename=%s' % basename
        return response


@auth.election_admin_required
@auth.requires_poll_features('compute_results_finished')
@require_http_methods(["GET"])
def zeus_proofs(request, election, poll):

    if not os.path.exists(poll.zeus_proofs_path()):
        poll.store_zeus_proofs()

    if settings.USE_X_SENDFILE:
        response = HttpResponse()
        response['Content-Type'] = ''
        response['X-Sendfile'] = poll.zeus_proofs_path()
        return response
    else:
        zip_data = file(poll.zeus_proofs_path())
        response = HttpResponse(zip_data.read(), mimetype='application/zip')
        zip_data.close()
        response['Content-Dispotition'] = 'attachment; filename=%s_proofs.zip' % election.uuid
        return response


@auth.election_admin_required
@auth.requires_poll_features('compute_results_finished')
@require_http_methods(["GET"])
def results_json(request, election, poll):
    data = poll.zeus.get_results()
    return HttpResponse(json.dumps(data, default=common_json_handler),
                        mimetype="application/json")
