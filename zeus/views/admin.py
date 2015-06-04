import copy
import datetime

from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib import messages

from zeus.reports import ElectionReport
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
    order_by=request.GET.get('order', 'created_at')
    order_type = request.GET.get('order_type', 'desc')
    if not order_by in ELECTION_TABLE_HEADERS:
        order_by = 'name'

    elections = Election.objects.administered_by(request.admin)
    nr_unfiltered_elections = elections.count()
    if nr_unfiltered_elections == 0:
        return HttpResponseRedirect(reverse('election_create'))

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

@auth.manager_or_superadmin_required
def elections_report(request):
    elections = Election.objects.filter(include_in_reports=True)
    save_path = getattr(settings, 'ZEUS_RESULTS_PATH', None)
    report = ElectionReport(elections)
    csv_path = getattr(settings, 'CSV_ELECTION_REPORT', None)
    if csv_path:
        report.parse_csv(csv_path)
    report.parse_object()
    # ext is not needed
    date = datetime.datetime.now()
    str_date = date.strftime("%Y-%m-%d")
    filename = 'elections_report_' + str_date
    report.make_output(save_path+filename)
    try:
        f = open(save_path+filename+'.csv', 'r')
    except IOError:
        message = "CSV file not found!"
        messages.error(request, message)
        return HttpResponseRedirect(reverse('admin_home'))
    response = HttpResponse(f, mimetype='application/csv')
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % filename
    return response
