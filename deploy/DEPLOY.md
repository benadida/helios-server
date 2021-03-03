
#  Deploy
```bash
        sudo chmod -R 777 /var/www
        sudo chmod o+u ./deploy/
        sudo chmod o+u ./deploy/*
        sudo python2 manage.py collectstatic
        sudo bash ./deploy/apache/apache2-service.sh
        sudo bash ./deploy/supervisor/supervisor-service.sh

```


