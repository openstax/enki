#!/bin/bash
set -e

BOOK_DIR=./data/test-book

# Build git PDF and web
KCOV_DIR=_kcov01 ./cli.sh $BOOK_DIR all-git-pdf 'philschatz/tiny-book/book-slug1' chemistry main
