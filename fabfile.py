"""
Deployment Fabric file

A fabric deployment script for Helios that assumes the following:
- locally, development is /web/helios-server
- remotely, a number of production setups 
- remotely, a number of staging setups
- all of these directories are git checkouts that have a proper origin pointer

Other assumptions that should probably change:
- both staging and production run under the same apache instance

Deployment is git and tag based, so:

fab staging_deploy:tag=v3.0.4,hosts="vote.heliosvoting.org"
fab production_deploy:tag=v3.0.5,hosts="vote.heliosvoting.org"

also to get the latest

fab production_deploy:tag=latest,hosts="vote.heliosvoting.org"

IMPORTANT: settings file may need to be tweaked manually
"""

from fabric.api import local, settings, abort, cd, run, sudo
from fabric.contrib.console import confirm

STAGING_SETUP = {
    'root' : "/web/staging/helios-server",
    'celery' : "/etc/init.d/staging-celeryd",
    'dbname' : "helios-staging"
    }

PRODUCTION_SETUPS = [
    {
        'root' : "/web/production/helios-server",
        'celery' : "/etc/init.d/celeryd",
        'dbname' : "helios"
        },
    {
        'root' : "/web/princeton/helios-server",
        'celery' : "/etc/init.d/princeton-celeryd",
        'dbname' : "princeton-helios"
        }
]
        
def run_tests():
    result = local("python manage.py test", capture=False)
    if result.failed:
        abort("tests failed, will not deploy.")

def check_tag(tag, path):
    result = local('git tag')
    if tag not in result.split("\n"):
        abort("no local tag %s" % tag)

    with cd(path):
        run('git pull origin master')
        run('git fetch --tags')
        result = run('git tag')
        if tag not in result.split("\n"):
            abort("no remote tag %s" % tag)

def get_latest(path):
    with cd(path):
        result = run('git pull')
        if result.failed:
            abort("on remote: could not get latest")

        result = run('git submodule init')
        if result.failed:
            abort("on remote: could not init submodules")

        result = run('git submodule update')
        if result.failed:
            abort("on remote: could not update submodules")
    
def checkout_tag(tag, path):
    with cd(path):
        result = run('git checkout %s' % tag)
        if result.failed:
            abort("on remote: could not check out tag %s" % tag)

        result = run('git submodule init')
        if result.failed:
            abort("on remote: could not init submodules")

        result = run('git submodule update')
        if result.failed:
            abort("on remote: could not update submodules")

def migrate_db(path):
    with cd(path):
        result = run('python manage.py migrate')
        if result.failed:
            abort("could not migrate")

def restart_apache():
    result = sudo('/etc/init.d/apache2 restart')
    if result.failed:
        abort("could not restart apache")

def restart_celeryd(path):
    result = sudo('%s restart' % path)
    if result.failed:
        abort("could not restart celeryd - %s " % path)

def deploy(tag, path):
    if tag == 'latest':
        get_latest(path=path)
    else:
        check_tag(tag, path=path)
        checkout_tag(tag, path=path)
    migrate_db(path=path)
    restart_apache()
    
def staging_deploy(tag):
    deploy(tag, path=STAGING_SETUP['root'])
    restart_celeryd(path = STAGING_SETUP['celery'])

def production_deploy(tag):
    production_roots = ",".join([p['root'] for p in PRODUCTION_SETUPS])
    if not confirm("Ready to deploy %s to %s?" % (tag, production_roots)):
        return
    run_tests()
    for prod_setup in PRODUCTION_SETUPS:
        deploy(tag, path = prod_setup['root'])
        restart_celeryd(path = prod_setup['celery'])
