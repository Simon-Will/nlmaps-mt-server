#!/usr/bin/env bash

if [ -z "$ASSETS" ]; then
    echo 'ERROR: ASSETS is not set.'
    exit 1
elif [ -z "$JOEYNMT_SERVER_PORT" ]; then
    echo 'ERROR: JOEYNMT_SERVER_PORT is not set.'
    exit 2
elif [ -z "$FLASK_ENV" ]; then
    echo 'ERROR: FLASK_ENV is not set.'
    exit 3
elif [ -z "$JOEYNMT_SERVER_REPO" ]; then
    echo 'ERROR: JOEYNMT_SERVER_REPO is not set.'
    exit 4
fi

mkdir -p "$ASSETS"

UWSGI_EXECUTABLE=$(which uwsgi)
PID_FILE=${UWSGI_PID_FILE:-"$ASSETS/uwsgi.pid"}

if [ ! -f "$UWSGI_EXECUTABLE" ]; then
    echo "$UWSGI_EXECUTABLE could not be not found." >&2
    exit 11
elif [ ! -x "$UWSGI_EXECUTABLE" ]; then
    echo "$UWSGI_EXECUTABLE is not executable." >&2
    exit 12
fi

echo 'Running uwsgi with the following environment'
echo '===================='
printenv
echo '===================='

start_uwsgi() {
    "$UWSGI_EXECUTABLE" "$JOEYNMT_SERVER_REPO/deploy/uwsgi.ini"
}

if [ -f "$PID_FILE" ]; then
    UWSGI_PID=$(< "$PID_FILE")
    FNAME=$(ps --no-headers -p "$UWSGI_PID" -o fname)
    if [ "$FNAME" = uwsgi ]; then
        echo "Gracefully restart existing uwsgi server with PID $UWSGI_PID"
        kill -HUP "$UWSGI_PID"
    else
        echo "Process with name $FNAME does not appear to be the uwsgi server."
        echo "Deleting old PID file $PID_FILE and starting a new uwsgi server."
        rm -f "$PID_FILE"
        start_uwsgi
    fi
else
    echo "PID file $PID_FILE does not exist."
    echo "Starting a new uwsgi server."
    start_uwsgi
fi
