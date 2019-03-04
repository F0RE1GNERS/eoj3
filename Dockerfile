FROM python:3.6-alpine3.6

ENV DJANGO_SETTINGS_MODULE eoj3.settings
ADD . /app

RUN apk add --update --no-cache build-base git nginx openssl curl unzip supervisor jpeg-dev zlib-dev freetype-dev nodejs nodejs-npm mariadb-dev postgresql-dev && \
    pip install --no-cache-dir -r /app/deploy/requirements.txt && \
    cd /app/static && npm install --prefix /lib/node_modules && npm install -g gulp && \
    apk del build-base --purge

RUN addgroup -g 12003 www && adduser -u 12000 -S -G www server

WORKDIR /app
ENTRYPOINT /app/deploy/entrypoint.sh
