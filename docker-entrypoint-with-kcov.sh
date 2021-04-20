#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -xe

if [[ $1 == 'shell' ]]; then
    docker-entrypoint.sh $@
else
    kcov /data/kcov-coverage-results/ docker-entrypoint.sh $@
fi