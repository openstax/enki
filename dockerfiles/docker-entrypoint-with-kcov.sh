#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# Trace if DEBUG is set
[[ $TRACE_ON ]] && set -x

if [[ $1 == 'shell' ]]; then
    bash
elif [[ $__CI_KCOV_MERGE_ALL__ ]]; then
    kcov --merge $@
elif [[ $KCOV_DIR != '' ]]; then
    [[ -d /data/$KCOV_DIR ]] || mkdir /data/$KCOV_DIR
    kcov \
        --skip-solibs \
        --exit-first-process \
        --include-path=/dockerfiles/docker-entrypoint.sh,/dockerfiles/steps/ \
        /data/$KCOV_DIR \
        docker-entrypoint.sh $@
    sleep 1 # Wait for files to flush?
else
    docker-entrypoint.sh $@
fi