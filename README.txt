The Helios Election Server
==========================

LICENSE: this code is released under the GPL v3 or later.

NEEDS:
- http://github.com/openid/python-openid
- rabbitmq 1.8
-- http://www.rabbitmq.com/debian.html
-- update the deb source
-- apt-get install rabbitmq-server

- celery 2.0.2 and django-celery 2.0.2 for async jobs
-- http://celeryq.org
-- apt-get install python-setuptools
-- easy_install celery
-- easy_install django-celery

