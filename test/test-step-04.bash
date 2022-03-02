#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

SOCI_DIR=../data/test-soci

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov04-a \
../enki $SOCI_DIR all-archive-web col11762 sociology latest

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov04-b \
../enki $SOCI_DIR archive-validate-cnxml
