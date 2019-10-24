# CHANGELOG
Updated to Python 3.7 and Django 2.2

## Python
* upgraded to python 3.7 with the help of the 2to3 utility
* [summary of changes introduced by Python 3.0](https://docs.python.org/3.7/whatsnew/3.0.html#porting-to-python-3-0)
* there were notable changes to:
    * print is a function
    * iterable lists
    * string and byte types
    * string formatting (though % substitution still works)
    


## Django
* upgraded to Django 2.2 one upgrade at a time
* all release notes are [here](https://docs.djangoproject.com/en/2.2/releases/)
* in particular note the changes to the major 2.0 release [Django 2.0 release notes](https://docs.djangoproject.com/en/2.2/releases/2.0/) 
* static files now collected using the [collectstatic utility](https://docs.djangoproject.com/en/2.2/howto/static-files/deployment/)
* url syntax changed
* rendering of widgets changed
* treatment of middleware changed in [1.10](https://docs.djangoproject.com/en/2.2/topics/http/middleware/#upgrading-pre-django-1-10-style-middleware)



## Celery
* upgraded to celery 4.3
* set it up as [recommended](https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#using-celery-with-django)
* using RabbitMQ as the message broker


## Dependencies
* started removing dependency on jquery and underscore so that javascript is vanilla


## Web workers
* the helios booth webworker is now a blob
* TODO: make the verifier worker a blob
