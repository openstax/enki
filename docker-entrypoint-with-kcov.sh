#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -xe

if [[ $1 == 'shell' ]]; then
    bash
elif [[ ${CI} ]]; then
    kcov /data/kcov-coverage-results/ docker-entrypoint.sh $@
else
    docker-entrypoint.sh $@
fi