
#   Supervisor
```bash
        mv var/www/helios-server/deploy/supervisor/celery-worker.conf /etc/supervisor/conf.d/
        mkdir /var/log/celery/
        supervisorctl reread
        supervisorctl update
        sudo supervisorctl start celery-worker


```

#   Apache2
```bash
        mv var/www/helios-server/deploy/apache/helios.conf /etc/apache2/sites-available
        sudo apachectl configtest
        sudo a2enmod rewrite
        sudo a2dissite 000-default.conf
        sudo a2ensite helios.conf
        sudo systemctl reload apache2
        chown www-data -R /var/www/helios-server
        chmod -R 750 /var/www/helios-server/*

```
