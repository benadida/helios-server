Errors faced during installation/configuration

First, read the instructions at INSTALL.md !

* Some python libraries where missing from the 'as is' Ubuntu 13.10 install and had to be installed:

````
sudo apt-get install python-dev
sudo apt-get install libldap2-dev
sudo apt-get install libsasl2-dev
sudo apt-get install python-ldap
sudo apt-get install gettext # to compile messages
sudo apt-get install libapache2-mod-wsgi # if using apache
pip install uwsgi
````

* Helios original settings file come with 
    'django.contrib.auth',
    'django.contrib.contenttypes',
apps commented out.

When I've tried to login using ldap user and password, I've got the following error:

```
DatabaseError: relation "auth_user" does not exist
LINE 1: ...ser"."last_login", "auth_user"."date_joined" FROM "auth_user...

...
Exception Type:     DatabaseError
Exception Value: 	

current transaction is aborted, commands ignored until end of transaction block
```
Enabling those apps solved the problem.

* Vote hash was not saving

Everything was working fine, except that the vote hash wasn't being saved.  This was happening because I didn't started the background job processor (issue kindly answered by Ben Adida)

Run the following command in a separate terminal window:

````
python manage.py celeryd
````

Dont' forget to install rabbitmq (https://www.rabbitmq.com/)

````
sudo apt-get install rabbitmq-server
````

* module' object has no attribute 'STATUS_UPDATES

Your auth model needs to declare STATUS_UPDATES