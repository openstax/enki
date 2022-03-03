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
# This actual command is really hacky since we are passing a list of directories into docker
SKIP_DOCKER_BUILD=1 \
../enki --data-dir $DATA_ROOT \
    --command __CI_KCOV_MERGE_ALL__ \
    --repo "./kcov-destination $BOOK_DIR_NAME/_kcov02-a $BOOK_DIR_NAME/_kcov02-b $BOOK_DIR_NAME/_kcov02-c $BOOK_DIR_NAME/_kcov03 $SOCI_DIR_NAME/_kcov04-a $SOCI_DIR_NAME/_kcov04-b $SOCI_DIR_NAME/_kcov05 $SOCI_DIR_NAME/_kcov07-a $SOCI_DIR_NAME/_kcov07-b" \
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
