set -e

# Draw the dependency graph PNG files
(cd ./build-concourse/ && npm run draw-graphs)

BOOK_DIR=./data/test-book
SOCI_DIR=./data/test-socio

[[ -d $BOOK_DIR ]] && rm -rf $BOOK_DIR
[[ -d $SOCI_DIR ]] && rm -rf $SOCI_DIR

# Build git PDF and web
CI=true                               ./cli.sh $BOOK_DIR all-git-pdf 'philschatz/tiny-book/book-slug1' chemistry main
CI=true START_AT_STEP=git-disassemble ./cli.sh $BOOK_DIR all-git-web 'philschatz/tiny-book/book-slug1' chemistry main

# Move coverage data (might not be necessary)
mkdir $SOCI_DIR && mv $BOOK_DIR/_kcov-coverage-results $SOCI_DIR

# Build archive web, PDF, and docx
CI=true                                      ./cli.sh $SOCI_DIR all-archive-web col11407 sociology latest
CI=true START_AT_STEP=archive-mathify                                   ./cli.sh $SOCI_DIR all-archive-pdf
CI=true START_AT_STEP=archive-gdocify STOP_AT_STEP=archive-convert-docx ./cli.sh $SOCI_DIR all-archive-gdoc
# kcov causes this step to hang so skip the CI=true (probably the pm2 mathml2svg background process)
START_AT_STEP=archive-convert-docx ./cli.sh $SOCI_DIR all-archive-gdoc

# Move coverage data out of the mounted volume the container used
[[ -d ./coverage/ ]] && rm -rf ./coverage/
mkdir ./coverage/
mv $SOCI_DIR/_kcov-coverage-results/* ./coverage/

echo "Open ./coverage/index.html in a browser to see the code coverage."

# bash <(curl -s https://codecov.io/bash) -s ./coverage/