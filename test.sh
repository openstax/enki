set -e

echo "WARN: Book Disassembly hangs without making a tweak. Comment a few lines and try again. See https://github.com/openstax/output-producer-service/pull/372"
sleep 10

# Draw the dependency graph PNG files
(cd ./build-concourse/ && npm run draw-graphs)

BOOK_DIR=./data/test-book
SOCI_DIR=./data/test-socio
KCOV_COLLECTOR=./data/kcov-collector
COVERAGE_DIR=./coverage

[[ -d $BOOK_DIR ]] && rm -rf $BOOK_DIR
[[ -d $SOCI_DIR ]] && rm -rf $SOCI_DIR
[[ -d $KCOV_COLLECTOR ]] && rm -rf $KCOV_COLLECTOR
[[ -d $COVERAGE_DIR ]] && rm -rf $COVERAGE_DIR

mkdir $KCOV_COLLECTOR

# Build git PDF and web
CI=true                               ./cli.sh $BOOK_DIR all-git-pdf 'philschatz/tiny-book/book-slug1' chemistry main
mv $BOOK_DIR/_kcov-coverage-results $KCOV_COLLECTOR/_kcov_results_1
export SKIP_DOCKER_BUILD=1
CI=true START_AT_STEP=git-disassemble ./cli.sh $BOOK_DIR all-git-web 'philschatz/tiny-book/book-slug1' chemistry main
mv $BOOK_DIR/_kcov-coverage-results $KCOV_COLLECTOR/_kcov_results_2

# Build archive web, PDF, and docx
CI=true                                      ./cli.sh $SOCI_DIR all-archive-web col11407 sociology latest
mv $SOCI_DIR/_kcov-coverage-results $KCOV_COLLECTOR/_kcov_results_3
CI=true START_AT_STEP=archive-mathify                                   ./cli.sh $SOCI_DIR all-archive-pdf
mv $SOCI_DIR/_kcov-coverage-results $KCOV_COLLECTOR/_kcov_results_4
CI=true START_AT_STEP=archive-gdocify STOP_AT_STEP=archive-convert-docx ./cli.sh $SOCI_DIR all-archive-gdoc
mv $SOCI_DIR/_kcov-coverage-results $KCOV_COLLECTOR/_kcov_results_5
# kcov causes this step to hang so skip the CI=true (probably the pm2 mathml2svg background process)
START_AT_STEP=archive-convert-docx ./cli.sh $SOCI_DIR all-archive-gdoc

# Merge all the kcov reports into one
__CI_KCOV_MERGE_ALL__=1 ./cli.sh $KCOV_COLLECTOR ./kcov-destination ./_kcov_results_1 ./_kcov_results_2 ./_kcov_results_3 ./_kcov_results_4 ./_kcov_results_5

# Move coverage data out of the mounted volume the container used
mkdir $COVERAGE_DIR
cp -R $KCOV_COLLECTOR/kcov-destination/* $COVERAGE_DIR

echo ""
echo "DONE: Open $COVERAGE_DIR/index.html in a browser to see the code coverage."

# Upload to codecov only if running inside CI
[[ $CI ]] && bash <(curl -s https://codecov.io/bash) -s $COVERAGE_DIR