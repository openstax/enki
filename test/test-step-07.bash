#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

SOCI_DIR=../data/test-soci

# The all-archive-web checksum step mangles the assembled.xhtml file so we have to start over
[[ -f $SOCI_DIR/archive-book/collection.assembled.xhtml ]] && rm $SOCI_DIR/archive-book/collection.assembled.xhtml

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov07-a \
../enki --data-dir $SOCI_DIR --command all-archive-pdf --start-at archive-assemble

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov07-b \
CORGI_ARTIFACTS_S3_BUCKET=dummy-test-bucket \
ARG_TARGET_PDF_FILENAME=dummy-test-pdf-filename \
../enki --data-dir $SOCI_DIR --command archive-pdf-metadata