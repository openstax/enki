#!/bin/bash
set -e

SOCI_DIR=./data/test-soci

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
./cli.sh $SOCI_DIR all-archive-web col11407 sociology latest