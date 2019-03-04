#!/bin/sh

APP=/app

#if [ ! -f "$DATA/public/avatar/default.png" ]; then
#    cp data/public/avatar/default.png $DATA/public/avatar
#fi
#
#if [ ! -f "$DATA/public/website/favicon.ico" ]; then
#    cp data/public/website/favicon.ico $DATA/public/website
#fi

echo "EOJ is starting..."
cp -r /build/static/node_modules/ /app/static/node_modules/
cd static && gulp less && cd ..

n=0
while [ $n -lt 5 ]
do
    python manage.py migrate --no-input &&
    n=$(($n+1))
    echo "Failed to migrate, going to retry..."
    sleep 8
done

addgroup -g 12003 www
adduser -u 12000 -S -G www server
chown -R www:server /generate /testdata /upload /repo /media

if [ -z "$DEBUG" ]; then
    echo "Entering production mode..."
    exec supervisord -c /app/deploy/supervisord.conf
else
    echo "Entering debug mode..."
    supervisord -c /app/deploy/supervisord.dev.conf
    exec python manage.py runserver 8000
fi
