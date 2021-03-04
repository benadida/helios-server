#!/bin/bash
if [[ `uname` == 'Linux' ]]; then
cp /var/www/helios-server/deploy/apache/helios.conf /etc/apache2/sites-available
sudo apachectl configtest
sudo adduser root  www-data
sudo -u postgres createuser www-data
sudo -u postgres psql -c 'alter user "www-data" with createdb;' postgres
sudo -u postgres psql helios -c 'GRANT ALL PRIVILEGES ON ALL TABLES in SCHEMA public to "www-data";' postgres
sudo -u postgres psql helios -c 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public to "www-data";' postgres
sudo -u postgres psql helios -c 'GRANT ALL PRIVILEGES ON ALL FUNCTIONS  IN SCHEMA public to "www-data";' postgres

sudo systemctl restart postgresql
sudo chmod 644 wsgi.py
sudo a2enmod rewrite
sudo a2dissite 000-default.conf
sudo a2ensite helios.conf
sudo a2enmod wsgi
sudo systemctl reload apache2
sudo ufw status
sudo systemctl reload apache2
sudo systemctl status apache2.service
sudo chown www-data -R /var/www/helios-server
sudo chown www-data:www-data /var/www/helios-server -R
sudo chmod -R 777 /var/www/helios-server/
fi
