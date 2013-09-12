from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse

from zeus import auth
from zeus.utils import *

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

from helios.view_utils import render_template
from zeus.forms import LoginForm
from zeus import auth


@auth.unauthenticated_user_required
def password_login_view(request):

    error = None
    if request.method == "GET":
        form = LoginForm()
    else:
        form = LoginForm(request.POST)

    request.session['auth_system_name'] = 'password'
    # TODO: protect from openredirect

    if form.is_valid():
        request.session[auth.USER_SESSION_KEY] = form._user_cache.pk
        return HttpResponseRedirect(reverse('admin_home'))

    return render_template(request,
                           'login',
                           {'form': form, 'error': error})


def logout(request):
    return_url = request.GET.get('next', reverse('home'))
    request.zeususer.logout(request)
    return HttpResponseRedirect(return_url)
