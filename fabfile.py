from fabric.api import *


def pull_update():
    with cd("/srv/xee"):
        sudo("git pull", user='zeus')
        sudo("python manage.py migrate helios", user='zeus')
        sudo("/etc/init.d/gunicorn restart")
        sudo("/etc/init.d/python-celery-xee restart")


def local_archive_update():
    """
    - Create archive from current local branch
    - Upload archive and move it to /srv/
    - Keep a copy of local settings
    - Archive current running code of zeus-server to /srv/archive/
    - Untar uploaded archive
    - Update zeus-server permissions
    - Migrate helios app
    - Restart gunicorn/celery services
    """
    with cd("/srv/"):
        sudo("cp zeus-server/local_settings.py ./")
        local("git archive --format=tar --out=code.tar " + \
              "--prefix=zeus-server/ `git rev-parse --abbrev-ref HEAD`")
        put("code.tar", "/tmp/")
        sudo("cp /tmp/code.tar /srv/")
        sudo("mv zeus-server " + \
             "archive/zeus-server-`date +\"%Y-%m-%d.%H:%M:%S\"`")
        sudo("tar -xf code.tar")
        sudo("cp local_settings.py zeus-server/")
        with cd("zeus-server"):
            sudo("chmod -R a+rx .")
            sudo("python manage migrate helios")
        sudo("/etc/init.d/gunicorn restart")
        sudo("/etc/init.d/python-celery restart")
