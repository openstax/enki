#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

SOCI_DIR=../data/test-soci

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov05 \
../enki --data-dir $SOCI_DIR --command all-archive-gdoc --start-at archive-gdocify --stop-at archive-convert-docx