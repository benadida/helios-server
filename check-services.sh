#!/bin/bash
SERVICES=('celeryd' 'celerybeat')
  
for service in ${SERVICES[@]}; do
    if ps ax | grep -v grep | grep $service > /dev/null
    then
        echo "$service service running, everything is fine"
    else
        echo "$service is not running"
        cd /var/www/helios-server && \
        source venv/bin/activate

        if [ "$service" == "celeryd" ]; then
            python manage.py celeryd --events --loglevel=INFO --concurrency=5 -f celery.log &
        else
            python manage.py $service --logleve=INFO -f $service.log &
        fi

        echo "$service is not running!" | mail -s "$service down" root
    fi
done
exit 0
