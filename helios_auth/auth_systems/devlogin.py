"""
Development Login Authentication
A simple development-only authentication system that allows login as user@example.com
without any external dependencies. Only works on localhost/127.0.0.1.
"""

from django.conf import settings
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse, re_path
from django.shortcuts import render

from helios_auth import url_names

import logging

# Login message shown in the auth selection box
LOGIN_MESSAGE = "Dev Login"
STATUS_UPDATES = False

def get_auth_url(request, redirect_url=None):
    """
    Get the URL to start the authentication process.
    For development login, we go directly to the login form.
    """
    # Security check: only allow on localhost/127.0.0.1
    if not _is_localhost(request):
        raise Http404("Development login only available on localhost")
    
    return reverse('auth@devlogin@login')

def get_user_info_after_auth(request):
    """
    Called after authentication to get user information.
    For dev login, we always return user@example.com
    """
    # Security check: only allow on localhost/127.0.0.1
    if not _is_localhost(request):
        raise Http404("Development login only available on localhost")
    
    # Return fixed development user info
    return {
        'type': 'devlogin',
        'user_id': 'user@example.com',
        'name': 'Development User',
        'info': {
            'email': 'user@example.com',
            'name': 'Development User'
        },
        'token': None
    }

def do_logout(user):
    """
    Log out the user. Nothing special needed for dev login.
    """
    return None

def update_status(token, message):
    """
    Update user status. Not applicable for dev login.
    """
    pass

def send_message(user_id, name, user_info, subject, body):
    """
    Send a message to the user. For dev login, we just log it.
    """
    logging.info(f"Dev login message to {user_id}: {subject}")

def check_constraint(constraint, user):
    """
    Check if user meets a constraint. Always true for dev login.
    """
    return True

def can_create_election(user_id, user):
    """
    Check if user can create elections. Always true for dev login.
    """
    return True

def devlogin_view(request):
    """
    Handle the development login form and process.
    """
    # Security check: only allow on localhost/127.0.0.1
    if not _is_localhost(request):
        raise Http404("Development login only available on localhost")
    
    if request.method == 'POST':
        # Process the login - always successful for dev
        # Redirect to the auth completion URL
        return HttpResponseRedirect(reverse(url_names.AUTH_AFTER))
    
    # Show the login form
    return render(request, 'auth/devlogin.html', {
        'dev_warning': True
    })

def _is_localhost(request):
    """
    Check if the request is coming from localhost.
    Returns True if the host is localhost, 127.0.0.1, or in DEBUG mode.
    """
    if not settings.DEBUG:
        return False
    
    host = request.get_host().split(':')[0]  # Remove port if present
    localhost_hosts = ['localhost', '127.0.0.1', 'testserver']
    
    # During testing, allow testserver explicitly or when TESTING flag is set
    if getattr(settings, 'TESTING', False) or host == 'testserver':
        return True
        
    return host in localhost_hosts

# URL patterns for this auth system
urlpatterns = [
    re_path(r'^devlogin/login$', devlogin_view, name='auth@devlogin@login'),
]