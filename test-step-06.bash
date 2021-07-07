#!/bin/bash
set -e

SOCI_DIR=./data/soci-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov05 \
START_AT_STEP=archive-gdocify \
STOP_AT_STEP=archive-convert-docx \
./cli.sh $SOCI_DIR all-archive-gdoc
