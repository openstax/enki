#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

VIRO_DIR=../data/test-viro

SKIP_DOCKER_BUILD=${SKIP_DOCKER_BUILD:-1} \
KCOV_DIR=_kcov11 \
../enki --clear-data --data-dir $VIRO_DIR --command all-git-epub --repo 'cnx-user-books/cnxbook-virology' --book-slug virology --style dummy --ref main
