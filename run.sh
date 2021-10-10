#!/bin/bash

docker run -p 5672:5672 -d rabbitmq:3
celery -A helios worker -l INFO
