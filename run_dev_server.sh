ZEUS_DEV_SERVER=1 PYTHONPATH=. uwsgi --ini ./uwsgi.ini --master-fifo=/tmp/zeus.fifo --req-logger=file:/tmp/zeus.uwsgi.log
