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
    read -r repo _rest <<< "$dirs_to_merge"
    merged_coverage="$repo/kcov-merged/coverage.json"
    merged_lines="$repo/kcov-merged/codecov.json"
    jq -sr '
        .[0] as $input |
        (.[1] | .coverage | to_entries) as $lines |
        $input | .files | .[] |
            .file as $file |
            .percent_covered as $percent_covered |
            $lines | .[] |
                .key as $relpath |
                select($file | endswith($relpath)) |
                .value | to_entries | .[] |
                    select(.value == 0) |
                    .key as $line |
                    "\($file | ltrimstr("/")): line \($line), col 1, Error - line not covered by tests. (coverage-error)"
    ' "$merged_coverage" "$merged_lines"
    jq -r '
        select((.percent_covered | tonumber) < 100) |
        error("Coverage must be at least 100%")
    ' "$merged_coverage"
elif [[ $KCOV_DIR != '' ]]; then
    [[ -d /tmp/build/0000000/$KCOV_DIR ]] || mkdir /tmp/build/0000000/$KCOV_DIR
    kcov \
        --skip-solibs \
        --exit-first-process \
        --include-path=/dockerfiles/docker-entrypoint.sh,/dockerfiles/steps/ \
        /tmp/build/0000000/$KCOV_DIR \
        docker-entrypoint.sh $@
    sleep 1 # Wait for files to flush?
else
    docker-entrypoint.sh $@
fi