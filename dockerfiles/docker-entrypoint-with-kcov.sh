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
    # Generate warnings instead of errors to support coverage < 100% (see issue)
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
                    "\($file | ltrimstr("/")): line \($line), col 1, Warning - line not covered by tests. (coverage-error)"
    ' "$merged_coverage" "$merged_lines"
    # Here we can decide what our minimum coverage should be
    jq -r '
        . as $input |
        100 as $min_coverage |
        ($input | .percent_covered | tonumber) as $percent_covered |
        select($percent_covered < $min_coverage) |
        error("Minimum coverage not met: \($percent_covered)/\($min_coverage)")
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