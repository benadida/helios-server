#!/bin/bash
if [[ `uname` == 'Linux' ]]; then
mv var/www/helios-server/deploy/supervisor/celery-worker.conf /etc/supervisor/conf.d/
mkdir /var/log/celery/
sudo chmod 766 /var/log/celery/
sudo service supervisor start
supervisorctl reread
supervisorctl update
sudo supervisorctl start celery-worker
fi
