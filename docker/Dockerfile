# temp stage
FROM python:3.6 as builder
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .

RUN apt update \
  && apt install -y --no-install-suggests --no-install-recommends libsasl2-dev libldap2-dev \
  && python -m venv /opt/venv \
  && pip install --upgrade pip \
  && pip install -r requirements.txt

# final stage
FROM python:3.6
COPY --from=builder /opt/venv /opt/venv
COPY . /app
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"

CMD ["/bin/bash", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
