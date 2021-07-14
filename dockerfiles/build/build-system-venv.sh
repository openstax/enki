#!/bin/sh
set -e

if [ ! -z "$GITPOD_HOST" ]; then
    mkdir -p $PROJECT_ROOT/venv/bin
    echo '# This is a no-op because we are running inside gitpod so no need for a virtualenv' > $PROJECT_ROOT/venv/bin/activate
else 
    python3 -m venv $PROJECT_ROOT/venv && \
      . $PROJECT_ROOT/venv/bin/activate && \
      pip3 install --no-cache-dir -U 'pip<20'
fi
