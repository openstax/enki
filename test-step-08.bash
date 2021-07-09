#!/bin/bash
set -e

BOOK_DIR=./data/test-book
SOCI_DIR=./data/test-soci
KCOV_COLLECTOR=./data/kcov-collector
COVERAGE_DIR=./coverage

mv \
    $BOOK_DIR/_kcov01 \
    $BOOK_DIR/_kcov02-a \
    $BOOK_DIR/_kcov02-b \
    $BOOK_DIR/_kcov03 \
    $SOCI_DIR/_kcov04-a \
    $SOCI_DIR/_kcov04-b \
    $SOCI_DIR/_kcov05-a \
    $SOCI_DIR/_kcov05-b \
    $SOCI_DIR/_kcov06 \
    $KCOV_COLLECTOR

# Merge all the kcov reports into one
SKIP_DOCKER_BUILD=1 \
__CI_KCOV_MERGE_ALL__=1 \
./cli.sh $KCOV_COLLECTOR ./kcov-destination \
    ./_kcov01 \
    ./_kcov02-a \
    ./_kcov02-b \
    ./_kcov03 \
    ./_kcov04-a \
    ./_kcov04-b \
    ./_kcov05-a \
    ./_kcov05-b \
    ./_kcov06 \
    ;

# Move coverage data out of the mounted volume the container used
mkdir $COVERAGE_DIR
cp -R $KCOV_COLLECTOR/kcov-destination/* $COVERAGE_DIR

echo ""
echo "DONE: Open $COVERAGE_DIR/index.html in a browser to see the code coverage."

# Upload to codecov only if running inside CI
[[ $CI || $CODECOV_TOKEN ]] && bash <(curl -s https://codecov.io/bash) -s $COVERAGE_DIR