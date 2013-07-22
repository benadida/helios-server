from helios.view_utils import render_template


def home(request):
    user = request.zeususer
    bad_login = request.GET.get('bad_login')
    return render_template(request, "zeus/home", {
        'menu_active': 'home',
        'user': user,
        'bad_login': bad_login
    })


def faqs_trustee(request):
    user = request.zeususer
    return render_template(request, "zeus/faqs_admin", {
        'menu_active': 'faqs',
        'submenu': 'admin',
        'user': user
    })


def faqs_voter(request):
    user = request.zeususer
    return render_template(request, "zeus/faqs_voter", {
      'menu_active': 'faqs',
      'submenu': 'voter',
      'user': user
    })


def resources(request):
    user = request.zeususer
    return render_template(request, "zeus/resources", {
        'menu_active': 'resources',
        'user': user
    })


def stats(request):
    user = request.zeususer
    uuid = request.GET.get('uuid', None)
    election = None

    if uuid:
        election = Election.objects.filter(uuid=uuid)
        if not (user and user.superadmin_p):
          election = election.filter(is_completed=True)

        election = election.defer('encrypted_tally', 'result')[0]

    if user and user.superadmin_p:
        elections = Election.objects.filter(is_completed=True)
    else:
        elections = Election.objects.filter(is_completed=True)

    elections = elections.order_by('-created_at').defer('encrypted_tally',
                                                        'result')

    return render_template(request, 'zeus/stats', {
        'menu_active': 'stats',
        'election': election,
        'uuid': uuid,
        'user': user,
        'elections': elections
    })
