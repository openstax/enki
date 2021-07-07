#!/bin/bash
set -e

SOCI_DIR=./data/test-soci

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov04 \
START_AT_STEP=archive-mathify \
./cli.sh $SOCI_DIR all-archive-pdf

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov05 \
CORGI_ARTIFACTS_S3_BUCKET=dummy-test-bucket \
ARG_TARGET_PDF_FILENAME=dummy-test-pdf-filename \
./cli.sh $SOCI_DIR archive-pdf-metadata