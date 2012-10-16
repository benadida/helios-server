"""
"""
from fabric.api import *

env.use_ssh_config = True
env.hosts = ['zeusprod']

def maketarball():
    with settings(warn_only=True):
        local("mkdir build")
        local("git archive master > build/zeus-`date -I`.tar")

def restart_gunicorn():
    sudo("/etc/init.d/gunicorn restart")

def uploadtarball():
    pass
