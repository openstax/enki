#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# Trace if DEBUG is set
[[ ${TRACE_ON} ]] && set -x

if [[ $1 == 'shell' ]]; then
    bash
elif [[ ${CI} ]]; then
    [[ -d /data/_kcov-coverage-results/ ]] || mkdir /data/_kcov-coverage-results/
    kcov --skip-solibs --exit-first-process --include-path=/usr/bin/docker-entrypoint.sh /data/_kcov-coverage-results/ docker-entrypoint.sh $@
else
    docker-entrypoint.sh $@
fi