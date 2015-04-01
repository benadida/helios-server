import copy

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings

from zeus.utils import render_template, ELECTION_TABLE_HEADERS,\
    get_filters, ELECTION_SEARCH_FIELDS, ELECTION_BOOL_KEYS_MAP
from zeus import auth

from helios.models import Election


@auth.election_admin_required
def home(request):
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    q_param = request.GET.get('q', '')

    default_elections_per_page = getattr(settings, 'ELECTIONS_PER_PAGE', 20)
    elections_per_page = request.GET.get('limit', default_elections_per_page)
    try:
        elections_per_page = int(elections_per_page)
    except:
        elections_per_page = default_elections_per_page
    order_by=request.GET.get('order', 'name')
    order_type = request.GET.get('order_type', 'desc')
    if not order_by in ELECTION_TABLE_HEADERS:
        order_by = 'name'

    elections = Election.objects.administered_by(request.admin)
    nr_unfiltered_elections = elections.count()
    if nr_unfiltered_elections == 0:
        return HttpResponseRedirect(reverse('election_create'))

    # fix filter function
    elections = elections.filter(get_filters(q_param, ELECTION_TABLE_HEADERS,
                                             ELECTION_SEARCH_FIELDS,
                                             ELECTION_BOOL_KEYS_MAP))
    elections = elections.order_by(order_by)
    if order_type == 'desc':
        elections = elections.reverse()

    context = {
        'elections_administered': elections,
        'election_table_headers': ELECTION_TABLE_HEADERS.iteritems(),
        'q': q_param,
        'page': page,
        'elections_per_page': elections_per_page,
    }
    return render_template(request, "index", context)
