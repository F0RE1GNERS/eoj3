#!/bin/sh

APP=/app

#if [ ! -f "$DATA/public/avatar/default.png" ]; then
#    cp data/public/avatar/default.png $DATA/public/avatar
#fi
#
#if [ ! -f "$DATA/public/website/favicon.ico" ]; then
#    cp data/public/website/favicon.ico $DATA/public/website
#fi

if [ -z "$MAX_WORKER_NUM" ]; then
    export CPU_CORE_NUM=$(grep -c ^processor /proc/cpuinfo)
    if [[ $CPU_CORE_NUM -lt 2 ]]; then
        export MAX_WORKER_NUM=2
    else
        export MAX_WORKER_NUM=$(($CPU_CORE_NUM))
    fi
fi

n=0
while [ $n -lt 5 ]
do
    python manage.py migrate --no-input &&
    n=$(($n+1))
    echo "Failed to migrate, going to retry..."
    sleep 8
done

addgroup -g 12003 www
adduser -u 12000 -S -G server server
chown -R www:server /generate /testdata /upload /repo /media

if [ -z "$DEBUG" ]; then
    exec supervisord -c /app/deploy/supervisord.conf
else
    supervisord -c /app/deploy/supervisord.dev.conf
    exec python manage.py runserver 8000
fi
