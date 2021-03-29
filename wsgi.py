import os
import sys
sys.path.append('/var/www')
sys.path.append('/var/www/helios-server')
from dotenv import load_dotenv
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
try:
    dotenv_path = os.path.join('/var/www/helios-server', '.env')
    load_dotenv(dotenv_path)
except:
    pass
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
