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
    supervisor \
    redis-server &&\
    rm -rf /var/lib/apt/lists/* && \
 	apt-get clean

RUN sed -i "s/bind .*/bind 127.0.0.1/g" /etc/redis/redis.conf
RUN sed -i "s/supervised no/supervised systemd/" /etc/redis/redis.conf
RUN sed -i "s/daemonize yes/daemonize no/" /etc/redis/redis.conf

COPY ./docker/supervisor/apache2-supervisor.conf /etc/supervisor/conf.d/apache2.conf
COPY ./docker/supervisor/celery-supervisor.conf /etc/supervisor/conf.d/celery-helios.conf
COPY ./docker/supervisor/redis-supervisor.conf /etc/supervisor/conf.d/redis-helios.conf

COPY ./docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY ./docker/apache/dummy-server.key /etc/ssl/private/dev-helios-apache.key
COPY ./docker/apache/dummy-server.crt /etc/ssl/certs/dev-helios-apache.crt
COPY ./docker/apache/helios-ssl.conf /etc/apache2/sites-available

RUN a2enmod rewrite && \
    a2enmod ssl && \
    a2dissite 000-default.conf && \
    a2dissite default-ssl.conf && \
    a2ensite helios-ssl.conf

RUN groupadd -r -g 1000 helios && useradd -r -g helios -u 1000 helios

WORKDIR /var/www/helios-server
RUN chown helios:helios /var/www/helios-server

EXPOSE 80
EXPOSE 443

ENTRYPOINT ["/docker-entrypoint.sh"]
