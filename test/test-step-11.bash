#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BUSI_DIR=../data/test-busi

SKIP_DOCKER_BUILD=${SKIP_DOCKER_BUILD:-1} \
KCOV_DIR=_kcov11 \
../enki --clear-data --data-dir $BUSI_DIR --command all-git-epub --repo 'openstax/osbooks-business-law' --book-slug business-law-i-essentials --ref main
