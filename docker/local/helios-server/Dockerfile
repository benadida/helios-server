FROM python:2.7-slim

ARG USER_ID=1000
ENV HOME=/home/django

RUN apt-get update && apt-get install -yy build-essential

# RUN pip install poetry==1.0.0
COPY ./helios-server /app
WORKDIR /app

COPY docker/local/helios-server/entrypoint.sh /entrypoint.sh
COPY docker/local/helios-server/start.sh /start.sh

# RUN poetry update && poetry install
RUN pip install -r requirements.txt

RUN addgroup --system --gid $USER_ID django \
    && adduser --system --home $HOME --uid $USER_ID --ingroup django django

RUN chown -R django /app $HOME
USER django

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start.sh"]
