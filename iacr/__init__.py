"""
This django app is meant only to connect the pieces of Helios and Auth that are specific to IACR
"""

import glue

import helios
import auth
import auth.models

helios.TEMPLATE_BASE = "iacr/templates/base.html"
helios.ADMIN_ONLY = True
helios.ADMIN = auth.models.User.get_or_create(user_type = 'password', user_id = 'benadida', info={'password':'test'})

# authentication limited to passwords
auth.ENABLED_AUTH_SYSTEMS = ['password']