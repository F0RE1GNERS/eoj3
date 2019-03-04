FROM python:3.6-alpine3.6 as eoj-base

ENV DJANGO_SETTINGS_MODULE eoj3.settings
ADD . /build

RUN apk add --update --no-cache build-base nginx openssl curl unzip supervisor jpeg-dev zlib-dev freetype-dev nodejs mariadb-dev postgresql-dev && \
    pip install --no-cache-dir -r /app/deploy/requirements.txt && \
    cd /build/static && npm install && \
    apk del build-base --purge

WORKDIR /app
ENTRYPOINT /app/deploy/entrypoint.sh
