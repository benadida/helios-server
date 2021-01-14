# Helios Election System

Helios is an end-to-end verifiable voting system. Project forked from [benadida/helios-server](https://github.com/benadida/helios-server)

[![Travis Build Status](https://travis-ci.org/benadida/helios-server.svg?branch=master)](https://travis-ci.org/benadida/helios-server)


## Installation 

You can install the Helios server easily by following 3 steps:

1.  ```git clone https://github.com/bmalbusca/helios-server.git```
  
2.  ```cd helios-server/```
   
3.   ```sudo sh helios-install.sh```

## Development

### OAuth integration

#### Examples

 To help developing a new authentication method (Fenix Oauth), was used [Source Trail](https://www.sourcetrail.com/).  This tool helps to find dependencies and the code diagram easily. From other forks, it is possible to found others  authentication integrations:

- https://github.com/openSUSE/helios-server/tree/master/helios_auth/auth_systems
- https://github.com/pirati-cz/helios-server/tree/master/helios_auth/auth_systems
- https://github.com/shirlei/helios-server/tree/master/helios_auth/auth_systems

For our case, other documentation is provided at [fenixedu](https://fenixedu.org/dev/tutorials/use-fenixedu-api-in-your-application/). [(other examples)](https://github.com/sergiofbsilva/sandbox/blob/master/API.md)



#### Intro

The authentication systems have dependencies with:	`models.py`,`tests.py` and `views.py`

In those files you will find the import and callbacks  of the available authentication systems:

- `models.py` is where the user authentication method is invoked
- `views.py` is where the user (front-end) is redirect to the urls available at the authentication method  

#### Getting started

The authentication need to be integrated as unique file, for example `our_auth.py`, and should have the following (standard) methods:

- `def can_create_election(user_id, user_info):` returns boolean
- `def get_auth_url(request, redirect_url):`  returns url
- `def get_user_info_after_auth(request):` returns object `{type:,user-id:, emai:,info:{}, token:{}}`

Other methods that we can implement is :

- `def send_message(user_id, name, user_info, subject, body):`- using a mail server 

 Some services are already reconized by Django. So, you don't need to specify a url because Django have a default redirecting url (that should be used when managing the service) . Search on google if your service is on of them. If not, you should create a route (function) to handle the redirecting from the oauth service.



#### Files to be updated

1. `helios-server/helios_auth/auth_systems/__init__.py` - Add your authentication system here
2. `helios-server/helios_auth/urls.py` - Add your urls (optional)
3. `helios-server/helios_auth/media/login-icons` - Add your authentication icon (42x42 png file with the same name as the auth) 
4. ` helios-server/settings.py` - Enable your default authentication system


### Celery integration

#### Installation

The `celery` and `rabbitmq` are automatically installed if you proceed helios-server installation via requirements file.

#### Dependencies

- `django-celery-results` - compatible, substitute of `djcelery` package 

##### Configuration
At `settings.py` add:

```python 
  INSTALLED_APPS = (
    ...,
    'django_celery_results',
)
```
```python 
    # set up celery                                                                                                                               
    CELERY_BROKER_URL = get_from_env('CELERY_BROKER_URL', 'amqp://localhost')                                                                     
    
    CELERY_RESULT_BACKEND = 'django-db'  
```
#### How to run

1. `python manage.py migrate django_celery_results`
2. `celery -A helios worker -S django -l info -E`
3. In other shell. `celery -A helios beat -l info`


#### References
Documentation
- https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
- https://docs.celeryproject.org/en/stable/getting-started/brokers/rabbitmq.html

Issues
- https://github.com/celery/django-celery-results/issues/19
- https://github.com/celery/django-celery-results/issues/102

for redis usage: https://tekshinobi.com/django-celery-rabbitmq-redis-broker-results-backend/

##  Dev groups

- [Helios Google groups](https://groups.google.com/g/helios-voting/)

