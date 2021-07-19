#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
# These dirs are relative to the mounted directory (DATA_ROOT)
BOOK_DIR_NAME=./test-book
SOCI_DIR_NAME=./test-soci
COVERAGE_DIR=../coverage

# Merge all the kcov reports into one
SKIP_DOCKER_BUILD=1 \
__CI_KCOV_MERGE_ALL__=1 \
../cli.sh $DATA_ROOT ./kcov-destination \
    $BOOK_DIR_NAME/_kcov01 \
    $BOOK_DIR_NAME/_kcov02-a \
    $BOOK_DIR_NAME/_kcov02-b \
    $BOOK_DIR_NAME/_kcov03 \
    $SOCI_DIR_NAME/_kcov04-a \
    $SOCI_DIR_NAME/_kcov04-b \
    $SOCI_DIR_NAME/_kcov05-a \
    $SOCI_DIR_NAME/_kcov05-b \
    $SOCI_DIR_NAME/_kcov06 \
    ;

# Move coverage data out of the mounted volume the container used
[[ -d $COVERAGE_DIR ]] || mkdir $COVERAGE_DIR
cp -R $DATA_ROOT/kcov-destination/* $COVERAGE_DIR

echo ""
echo "DONE: Open $COVERAGE_DIR/index.html in a browser to see the code coverage."

# Upload to codecov only if running inside CI
if [[ $CI || $CODECOV_TOKEN ]]; then
    cd ..
    bash <(curl -s https://codecov.io/bash) -s ./coverage
fi
