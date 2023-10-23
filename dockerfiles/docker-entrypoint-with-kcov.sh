#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# Trace if DEBUG is set
[[ $TRACE_ON ]] && set -x && export PS4='+ [${BASH_SOURCE##*/}:${LINENO}] '

if [[ $1 == 'shell' ]]; then
    bash
elif [[ $1 == '__CI_KCOV_MERGE_ALL__' ]]; then
    dirs_to_merge=''
    shift 1
    while [ -n "$1" ]; do
        case "$1" in
            --repo) ;;
            --book-slug) shift ;;
            *)
                dirs_to_merge="$dirs_to_merge $1"
            ;;
        esac
        shift
    done
    if [[ $dirs_to_merge = '' ]]; then
        echo "BUG: Did not specify which directories to merge"
        exit 1
    fi
    kcov --merge $dirs_to_merge
elif [[ $KCOV_DIR != '' ]]; then
    [[ -d /data/build/data/$KCOV_DIR ]] || mkdir /data/build/data/$KCOV_DIR
    kcov \
        --skip-solibs \
        --exit-first-process \
        --include-path=/dockerfiles/docker-entrypoint.sh,/dockerfiles/steps/ \
        /data/build/data/$KCOV_DIR \
        docker-entrypoint.sh $@
    sleep 1 # Wait for files to flush?
else
    docker-entrypoint.sh $@
fi