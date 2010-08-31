"""
Deployment Fabric file

A fabric deployment script for Helios that assumes the following:
- locally, development is /web/helios-server
- remotely, production is /web/production/helios-server
- remotely, staging is /web/staging/helios-server

Deployment is git and tag based, so

fab staging_deploy:tag=v3.0.4,hosts="vote.heliosvoting.org"
fab production_deploy:tag=v3.0.5,hosts="vote.heliosvoting.org"
"""

from fabric.api import local, settings, abort, cd, run
from fabric.contrib.console import confirm

STAGING_DIR = "/web/staging/helios-server"
PRODUCTION_DIR = "/web/production/helios-server"

def run_tests():
    result = local("python manage.py test", capture=False)
    if result.failed:
        abort("tests failed, will not deploy.")

def check_tag(tag, path):
    result = local('git tag')
    if tag not in result.split("\n"):
        abort("no local tag %s" % tag)

    with cd(path):
        result = run('git tag')
        if tag not in result.split("\n"):
            abort("no remote tag %s" % tag)

def checkout_tag(tag, path):
    pass

def migrate_db(path):
    pass

def restart_apache():
    pass

def deploy_staging(tag):
    confirm("Ready to deploy %s to staging?" % tag)
    run_tests()
    check_tag(tag, path=STAGING_DIR)
    
