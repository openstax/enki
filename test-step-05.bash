#!/bin/bash
set -e

SOCI_DIR=./data/soci-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov04 \
START_AT_STEP=archive-mathify \
./cli.sh $SOCI_DIR all-archive-pdf
