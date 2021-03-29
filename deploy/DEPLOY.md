
#  Deploy

To serve this Django App with Apache you will need to use WSGI and source a folder with all static files. Here is an example of deploying helios-server using raw bash script:

```bash
    sudo chmod -R 777 /var/www
    sudo chmod o+u ./deploy/
    sudo chmod o+u ./deploy/*
    source .venv/bin/activate
    sudo -E python2 manage.py collectstatic
    sudo mkdir static/auth
    sudo mv static/login-icons/ static/auth
    sudo bash ./deploy/apache/apache2-service.sh
    sudo bash ./deploy/supervisor/supervisor-service.sh
```


