"""
Deployment Fabric file

A fabric deployment script for Helios that assumes the following:
- locally, development is /web/helios-server
- remotely, production is /web/production/helios-server
- remotely, staging is /web/staging/helios-server
- all of these directories are git checkouts that have a proper origin pointer

Other assumptions that should probably change:
- both staging and production run under the same apache instance

Deployment is git and tag based, so:

fab staging_deploy:tag=v3.0.4,hosts="vote.heliosvoting.org"
fab production_deploy:tag=v3.0.5,hosts="vote.heliosvoting.org"

IMPORTANT: settings file may need to be tweaked manually
"""

from fabric.api import local, settings, abort, cd, run, sudo
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
    with cd(path):
        result = run('git checkout %s' % tag)
        if result.failed:
            abort("on remote: could not check out tag %s" % tag)

def migrate_db(path):
    with cd(path):
        result = run('python manage.py migrate')
        if result.failed:
            abort("could not migrate")

def restart_apache():
    result = sudo('/etc/init.d/apache2 restart')
    if result.failed:
        abort("could not restart apache")

def deploy(tag, path):
    confirm("Ready to deploy %s to %s?" % (tag,path))
    run_tests()
    check_tag(tag, path=path)
    checkout_tag(tag, path=path)
    #migrate_db(path=path)
    restart_apache()
    
def staging_deploy(tag):
    deploy(tag, path=STAGING_DIR)

def production_deploy(tag):
    deploy(tag, path=PRODUCTION_DIR)
