FROM python:3.6-alpine3.6

ENV DJANGO_SETTINGS_MODULE eoj3.settings

ADD . /app
WORKDIR /app

RUN apk add --update --no-cache build-base nginx openssl curl unzip supervisor jpeg-dev zlib-dev freetype-dev && \
    pip install --no-cache-dir -r /app/deploy/requirements.txt && \
    apk del build-base --purge

ENTRYPOINT /app/deploy/entrypoint.sh
