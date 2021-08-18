#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

SOCI_DIR=../data/test-soci

# The all-archive-web checksum step mangles the assembled.xhtml file so we have to start over
[[ -f $SOCI_DIR/archive-book/collection.assembled.xhtml ]] && rm $SOCI_DIR/archive-book/collection.assembled.xhtml

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov07-a \
START_AT_STEP=archive-assemble \
../cli.sh $SOCI_DIR all-archive-pdf

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov07-b \
CORGI_ARTIFACTS_S3_BUCKET=dummy-test-bucket \
ARG_TARGET_PDF_FILENAME=dummy-test-pdf-filename \
../cli.sh $SOCI_DIR archive-pdf-metadata