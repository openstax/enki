#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# Trace if DEBUG is set
[[ ${TRACE_ON} ]] && set -x

if [[ $1 == 'shell' ]]; then
    bash
elif [[ ${CI} ]]; then
    kcov /data/_kcov-coverage-results/ docker-entrypoint.sh $@
else
    docker-entrypoint.sh $@
fi