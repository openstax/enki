#!/bin/sh
set -e

VENV_ROOT=${VENV_ROOT:-/openstax/venv}

if [ ! -z "$GITPOD_HOST" ]; then
    mkdir -p $VENV_ROOT/bin
    echo '# This is a no-op because we are running inside gitpod so no need for a virtualenv' > $VENV_ROOT/bin/activate
else
    python3 -m venv $VENV_ROOT
    # shellcheck disable=SC1090
    . $VENV_ROOT/bin/activate
    pip3 install --no-cache-dir -U 'pip<20'
fi
