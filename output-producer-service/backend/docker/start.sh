#! /usr/bin/env sh
# shellcheck source=/dev/null
set -e

MODULE_NAME=${MODULE_NAME:-app.main}
CALLABLE_NAME=${CALLABLE_NAME:-server}
GUNICORN_CONF=${GUNICORN_CONF:-/gunicorn.conf}
PRE_START_PATH=${PRE_START_PATH:-/app/bin/prestart.sh}

export APP_MODULE=${APP_MODULE:-"$MODULE_NAME:$CALLABLE_NAME"}
export GUNICORN_CONF=${GUNICORN_CONF}
export PRE_START_PATH=${PRE_START_PATH}

if [ -f "$PRE_START_PATH" ] ; then
    echo "Running script $PRE_START_PATH"
    . "$PRE_START_PATH"
else
    echo "There is no script $PRE_START_PATH"
fi

# Start Gunicorn
exec gunicorn -k uvicorn.workers.UvicornWorker -c "$GUNICORN_CONF" "$APP_MODULE"
