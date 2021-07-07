#!/bin/bash
set -e

SOCI_DIR=./data/soci-book

# kcov causes this step to hang so skip the KCOV_DIR (probably the pm2 mathml2svg background process)
SKIP_DOCKER_BUILD=1 \
START_AT_STEP=archive-convert-docx \
./cli.sh $SOCI_DIR all-archive-gdoc
