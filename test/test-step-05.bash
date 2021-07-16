#!/bin/bash
set -e
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"
[[ ${TRACE_ON} ]] && set -x

SOCI_DIR=../data/test-soci

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov05-a \
START_AT_STEP=archive-mathify \
../cli.sh $SOCI_DIR all-archive-pdf

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov05-b \
CORGI_ARTIFACTS_S3_BUCKET=dummy-test-bucket \
ARG_TARGET_PDF_FILENAME=dummy-test-pdf-filename \
../cli.sh $SOCI_DIR archive-pdf-metadata