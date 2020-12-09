#!/bin/bash
if [[ `uname` == 'Linux' ]]; then

echo Helios Debian-Ubuntu installation 

sudo apt-get install -y build-essential
sudo apt-get update
sudo apt-get install -y python-setuptools
sudo apt-get install -y python-pip
sudo pip install virtualenv
sudo virtualenv venv;sudo virtualenv -p /usr/bin/python2.7 venv; source venv/bin/activate

#sudo /bin/sh -c 'apt-get install -y aptitude'
sudo apt-get install -y apache2
sudo apt-get install -y postgresql postgresql-contrib
sudo apt-get install -y libsasl2-dev python-dev libldap2-dev libssl-dev
sudo apt-get install -y python-ldap gettext libapache2-mod-wsgi
sudo apt-get install -y apache2-utils ssl-cert libapache2-mod-shib2
sudo apt-get install -y ufw
sudo apt-get install -y rabbitmq-server
sudo apt-get install -y tmux

sudo pip install south
sudo pip install uwsgi
sudo pip install httplib2
sudo pip install oauth2client
sudo pip install python_openid

sudo apt update
sudo pip install -r requirements.txt
sudo apt-get install -y postfix

sudo -u debian createuser
sudo -u createuser --superuser root
sudo -u postgres createdb helios
sudo ./reset.sh

echo Done
fi
