#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
# These dirs are relative to the mounted directory (DATA_ROOT)
BOOK_DIR_NAME=./test-book
BUSI_DIR_NAME=./test-busi
COVERAGE_DIR=../coverage

# Merge all the kcov reports into one
# This actual command is really hacky since we are passing a list of directories into docker
SKIP_DOCKER_BUILD=1 \
../enki \
    --keep-data \
    --data-dir $DATA_ROOT \
    --command __CI_KCOV_MERGE_ALL__ \
    --repo "./kcov-destination $BOOK_DIR_NAME/_kcov02-a $BOOK_DIR_NAME/_kcov02-b $BOOK_DIR_NAME/_kcov02-c $BOOK_DIR_NAME/_kcov02-d $BOOK_DIR_NAME/_kcov02-e $BOOK_DIR_NAME/_kcov03 $BOOK_DIR_NAME/_kcov05-a $BOOK_DIR_NAME/_kcov05-b $BUSI_DIR_NAME/_kcov11-a $BUSI_DIR_NAME/_kcov11-b" --book-slug "doesnotmatter" \
    ;

# Move coverage data out of the mounted volume the container used
[[ -d $COVERAGE_DIR ]] || mkdir $COVERAGE_DIR
cp -R $DATA_ROOT/kcov-destination/* $COVERAGE_DIR

echo ""
echo "DONE: Open $COVERAGE_DIR/index.html in a browser to see the code coverage."

# Upload to codecov only if running inside CI
if [[ $CI || $CODECOV_TOKEN ]]; then
    bash <(curl -s https://codecov.io/bash) -Z -s $PWD/../coverage -s $PWD/../bakery-js/coverage
fi

echo "Checking if bakery-js files are formatted properly. If not, run 'npm run lint:fix'"
npm --prefix ../bakery-js run lint