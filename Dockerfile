FROM python:2.7

ENV PYTHONUNBUFFERED 1

RUN DEBIAN_FRONTEND='noninteractive' apt-get update -qq && apt-get install -y postgresql-client-9.4
ARG USER_ID=1000
RUN adduser --disabled-password --quiet --uid ${USER_ID} --gecos Helios helios

USER helios
ENV HOME /home/helios

RUN mkdir $HOME/server
WORKDIR $HOME/server
