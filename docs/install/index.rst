Zeus quick install guide
========================

This guide focuses on providing detailed instructions for users who want to
install and deploy the ``zeus`` voting platform on their own machine. The
following steps were tested on a fresh installation of Ubuntu 12.04 LTS but
should also work for any Debian/Ubuntu based distro that provides the required 
packages.


Install prerequisite packages
*****************************

* Add a ppa repository to be able to install ``Django==1.4``::

    $ sudo add-apt-repository ppa:dholbach/ppa
    $ sudo apt-get update

* Install the required packages::

  $ sudo apt-get install python bzip2 postgresql apache2 libapache2-mod-xsendfile rabbitmq-server python-django-picklefield python-psycopg2 unzip python-celery python-django-celery python-kombu python-django gunicorn python-pyicu python-django-pagination python-django-south python-openid python-gmpy


Create a new database
*********************

Create a postgres user and a database owned by that user. Keep reference to 
username, password and database name, since you will need to place them in
your local zeus configuration file::

  $ sudo su -l postgres
  (postgres)$ createuser <username> -P -S -d -R
  (postgres)$ createdb <databasename> -E utf8 -l C -T template0 -O <username>;
  (postgres)$ exit;


Download and extract zeus code
******************************

Download and extract the zeus codebase

.. code-block:: bash

  $ sudo mkdir -p /srv/ && cd /srv/
  $ sudo wget https://github.com/grnet/zeus/archive/master.zip
  $ sudo unzip master.zip && sudo mv zeus-master zeus-server
  $ sudo chmod +x zeus-server/manage.py


Configure zeus
**************

* Copy the example settings file::

    $ sudo cp /srv/zeus-server/local_settings.py.example /srv/zeus-server/local_settings.py

  ``local_settings.py`` is the file that contains your custom ``zeus`` configuration.

  Consider changing the following settings to match your deployment configuration:

    * ``ADMINS``
    * ``ELECTION_ADMINS``
    * ``DATABASES``
    * ``EMAIL_*`` settings
    * ``DEFAULT_FROM_EMAIL``
    * ``SITE_DOMAIN``
    * ``SECRET_KEY``

* Create an instance of the ``Institution`` model in order to be able to create
  demo accounts::

    $ cd /srv/zeus-server
    $ python manage.py shell
    >>> from zeus.models.zeus_models import Institution
    >>> Institution.objects.create(name="DEMO")
    >>> exit()


Apache configuration
********************

* Create a self signed certificate (you can skip this step you have one already)::

  $ cd ~/
  $ sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout zeus.key -out zeus.crt
  $ sudo mv zeus.crt /etc/ssl/
  $ sudo mv zeus.key /etc/ssl/private

* Create a zeus vhost::

  $ sudo cp /srv/zeus-server/conf/apache2_zeus /etc/apache2/sites-available/zeus

* Edit ``/etc/apache2/sites-available/zeus`` and replace the domains to match your 
  deployment.

* Enable required mods::

  $ sudo a2enmod rewrite 
  $ sudo a2enmod ssl
  $ sudo a2enmod xsendfile 
  $ sudo a2enmod proxy
  $ sudo a2enmod proxy_http
  $ sudo a2enmod proxy_connect

* Finally, enable zeus virtual host::

  $ sudo a2ensite zeus


Celery configuration
********************

* Since celery package does not contain an ``init.d`` script we should create 
  and configure one::

  $ sudo cp /srv/zeus-server/conf/celeryd_debian_default /etc/default/celeryd
  $ sudo cp /srv/zeus-server/conf/celeryd_initd /etc/init.d/celeryd
  $ sudo chmod +x /etc/init.d/celeryd
  $ sudo adduser --disabled-login celeryd -q --no-create-home
  $ sudo mkdir -p /var/run/celery
  $ sudo mkdir -p /var/log/celery
  $ sudo chown celeryd:celeryd /var/run/celery /var/log/celery


Gunicorn configuration
**********************

Copying the sample gunicorn config should be enough.

.. code-block:: bash

  $ sudo cp /srv/zeus-server/conf/gunicorn_zeus /etc/gunicorn.d/zeus


Prepare zeus directories
************************

Zeus requires the following directories to exist with the specified
permissions::
  
  $ sudo mkdir -p /usr/share/zeus/zeus_mixes
  $ sudo mkdir -p /usr/share/zeus_proofs
  $ sudo mkdir -p /var/run/zeus-celery
  $ sudo chmod a+r /var/run/zeus-celery

  $ sudo chown www-data /var/run/zeus-celery
  $ sudo chown -R celeryd:celeryd /usr/share/zeus /usr/share/zeus_proofs
  $ sudo chmod a+r -R /usr/share/zeus /usr/share/zeus_proofs


Initialize zeus database
************************

.. code-block:: bash

  $ cd /srv/zeus-server
  $ sudo python manage.py syncdb --all
  $ sudo python manage.py migrate --fake


Create zeus users
*****************

Create an election admin user. This will be used later on to create your first 
election.

.. code-block:: bash

  $ cd /srv/zeus-server
  $ python manage.py manage_users --create-institution "ZEUS"
  $ python manage.py manage_users --create-user <username> --institution=1


Restart all services
********************

.. code-block:: bash

  $ sudo service apache2 restart
  $ sudo service gunicorn restart
  $ sudo service celeryd restart


Login and create an election
*****************************

At this point you should be able to access the zeus platform from the domain 
you chose to deploy to. You can login using the credentials you provided to 
the user creation step above at the following url::

  https://<DOMAIN_NAME>/auth/password/login

and create your first election by visiting::

  https://<DOMAIN_NAME>/helios/elections/new

