#!/bin/bash
if [[ `uname` == 'Linux' ]]; then

echo #####################
echo Helios Debian-Ubuntu installation
echo #####################

sudo apt-get install -y build-essential
sudo apt-get update
sudo apt-get install -y python-setuptools
sudo apt-get install -y python-pip
sudo pip install --upgrade pip
sudo pip install virtualenv
sudo virtualenv .venv && sudo chmod 777 -R $(pwd)/.venv/
source $(pwd)/.venv/bin/activate

activate(){
	. ./.venv/bin/activate

	sudo apt-get install -y apache2
	sudo apt-get install -y postgresql postgresql-contrib
	sudo apt-get install -y libsasl2-dev python-dev libldap2-dev libssl-dev
	sudo apt-get install -y python-ldap gettext libapache2-mod-wsgi
	sudo apt-get install -y apache2-utils ssl-cert libapache2-mod-shib2
	sudo apt-get install -y ufw
	sudo apt-get install -y rabbitmq-server
	sudo apt-get install -y tmux
	sudo apt-get install -y supervisor

	sudo pip install south
	sudo pip install uwsgi
	sudo pip install httplib2
	sudo pip install oauth2client
	sudo pip install python_openid

	sudo apt update
	sudo pip install -r requirements.txt

	sudo -u postgres createuser $(whoami)
	sudo -u postgres createuser root
	sudo -u postgres psql -c 'alter user '$(whoami)' with createdb;' postgres
	sudo -u postgres createdb -O $(whoami) helios

	echo Enviroment setup is Done!
	sudo apt-get update
	echo Updating...
	sudo apt-get install -f
	pip install -r requirements.txt


}
activate

echo Reset database...
sudo chmod 777 reset.sh
sh -x ./reset.sh
echo Installation Finished!
echo #####################
echo Add missing installation: sudo apt-get install -y postfix
echo #####################
echo Your Server IP: $(hostname -i)
echo Run Command: python manage.py runserver 0.0.0.0:8000
fi
