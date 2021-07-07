#!/bin/bash
set -e

BOOK_DIR=./data/test-book
SOCI_DIR=./data/test-socio
KCOV_COLLECTOR=./data/kcov-collector
COVERAGE_DIR=./coverage

mv $BOOK_DIR/_kcov01 $BOOK_DIR/_kcov02 $KCOV_COLLECTOR
mv $SOCI_DIR/_kcov03 $SOCI_DIR/_kcov04 $SOCI_DIR/_kcov05 $KCOV_COLLECTOR

# Merge all the kcov reports into one
__CI_KCOV_MERGE_ALL__=1 ./cli.sh $KCOV_COLLECTOR ./kcov-destination ./_kcov01 ./_kcov02 ./_kcov03 ./_kcov04 ./_kcov05

# Move coverage data out of the mounted volume the container used
mkdir $COVERAGE_DIR
cp -R $KCOV_COLLECTOR/kcov-destination/* $COVERAGE_DIR

echo ""
echo "DONE: Open $COVERAGE_DIR/index.html in a browser to see the code coverage."

# Upload to codecov only if running inside CI
[[ $CI || $CODECOV_TOKEN ]] && bash <(curl -s https://codecov.io/bash) -s $COVERAGE_DIR