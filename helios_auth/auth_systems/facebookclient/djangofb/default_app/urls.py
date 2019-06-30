from django.conf.urls import url

from .views import canvas

urlpatterns = [
    url(r'^$', canvas),
]
