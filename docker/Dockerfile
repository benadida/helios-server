FROM ubuntu:18.04

RUN \
 	apt-get update && \
 	apt-get -y dist-upgrade && \
  	apt-get install -y -q \
    python-minimal \
    python-pip \
    python-virtualenv \
    python-ldap \
    python-dev \
    libsasl2-dev \
    libldap2-dev \
    apache2 \
    libapache2-mod-wsgi \
    build-essential \
    gettext \
    supervisor &&\
 	apt-get clean

EXPOSE 80
EXPOSE 443

COPY ./docker/supervisor/apache2-supervisor.conf /etc/supervisor/conf.d/apache2.conf
COPY ./docker/supervisor/celery-supervisor.conf /etc/supervisor/conf.d/celery-helios.conf

COPY ./docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY ./docker/apache/dummy-server.key /etc/ssl/private/dev-helios-apache.key
COPY ./docker/apache/dummy-server.crt /etc/ssl/certs/dev-helios-apache.crt
COPY ./docker/apache/helios-ssl.conf /etc/apache2/sites-available

RUN a2enmod rewrite
RUN a2enmod ssl
RUN a2dissite 000-default.conf
RUN a2dissite default-ssl.conf
RUN a2ensite helios-ssl.conf

RUN groupadd -r -g 1000 helios && useradd -r -g helios -u 1000 helios

WORKDIR /var/www/helios-server
RUN chown helios:helios /var/www/helios-server

ENTRYPOINT ["/docker-entrypoint.sh"]
