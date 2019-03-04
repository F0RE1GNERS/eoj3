FROM python:3.6-alpine3.6

ENV DJANGO_SETTINGS_MODULE eoj3.settings
ADD . /build
ADD . /app

RUN apk add --update --no-cache build-base git nginx openssl curl unzip supervisor jpeg-dev zlib-dev freetype-dev nodejs nodejs-npm mariadb-dev postgresql-dev && \
    pip install --no-cache-dir -r /build/deploy/requirements.txt && \
    cd /build/static && npm install --prefix /static/node_modules && npm install -g gulp && \
    apk del build-base --purge

WORKDIR /app
ENTRYPOINT /app/deploy/entrypoint.sh
