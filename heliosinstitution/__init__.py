"""
Script for create/update app permissions after migrations
Author: Shirlei Chaves - shirlei@gmail.com
Version 1.0 - 03/2015

with ideas from here:
http://www.geekrant.org/2014/04/19/programmatically-create-django-security-groups/
and here:
http://devwithpassion.com/felipe/south-django-permissions/

"""
from south.signals import post_migrate
from django.db.models import signals
from django.contrib.auth.models import Group, Permission
import models 

verbosity = 2

def update_permissions_after_migration(app, **kwargs):

    from django.conf import settings
    from django.db.models import get_app, get_models
    from django.contrib.auth.management import create_permissions
    
    create_permissions(get_app(app), get_models(), 2 if settings.DEBUG else 0)

    if app == "heliosinstitution":
        """
        Permissions must exist in app model, otherwise an error
        will be thrown
        """
        heliosinstitution_group_permissions = {
            "Institution Admin" : [
                "delegate_institution_mngt",
                "revoke_institution_mngt",
                "delegate_election_mngt",
                "revoke_election_mngt"
            ],
            "Election Admin": [
            ],
        }
        if verbosity>0:
            print "Initialising data post_migrate"
        for group in heliosinstitution_group_permissions:
            role, created = Group.objects.get_or_create(name=group)
            if verbosity > 1 and created:
                print 'Creating group', group
                for perm in heliosinstitution_group_permissions[group]:
                    role.permissions.add(Permission.objects.get(codename=perm))
                    if verbosity > 1:
                        print 'Permitting', group, 'to', perm
                        role.save()  


post_migrate.connect(update_permissions_after_migration)
