#!/bin/bash
if [[ `uname` == 'Linux' ]]; then
cp /var/www/helios-server/deploy/apache/helios.conf /etc/apache2/sites-available
sudo apachectl configtest
sudo a2enmod rewrite
sudo a2dissite 000-default.conf
sudo a2ensite helios.conf
sudo systemctl reload apache2
sudo chown www-data -R /var/www/helios-server
sudo chmod -R 750 /var/www/helios-server/*
fi
