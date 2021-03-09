import os
from dotenv import load_dotenv
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
try:
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    FENIX_CLIENT_ID='1132965128044819'
    FENIX_CLIENT_SECRET='INHng1jafDlaWbFpXeopI+CYwAdRz3Et+mDK2DZNNGiEWz6N8/VwyrC9/6PVBGLff6FHF8p+/G2TvpLPOgcoVQ=='
    URL_HOST='http://debian.athens-dev.al.vps.tecnico.ulisboa.pt'
    EMAIL_HOST='mail.tecnico.ulisboa.pt'
    EMAIL_PORT=465
    EMAIL_HOST_USER='ist181866'
    EMAIL_HOST_PASSWORD='Neo4j2021'
except RuntimeError as err: 
    print('*Alert* Deployment environment not found!', err)

application = get_wsgi_application()
