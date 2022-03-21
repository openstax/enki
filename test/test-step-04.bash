#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

SOCI_DIR=../data/test-soci

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov04-a \
../enki --clear-data --data-dir $SOCI_DIR --command all-archive-web --repo col11762 --style sociology --ref latest

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov04-b \
../enki --keep-data --data-dir $SOCI_DIR --command archive-validate-cnxml
