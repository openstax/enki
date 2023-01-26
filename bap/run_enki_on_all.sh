#!/bin/bash

set -e

while [ -n "$1" ]; do
  case "$1" in
    --command) 
      shift; arg_command=$1
    ;;
    *)
      echo "Invalid argument $1"
      exit 1
    ;;
  esac
  shift
done

[[ $arg_command ]] || ( echo "ERROR: A command was not provided. Typical examples are 'all-git-pdf' or 'all-git-web' or 'rex-preview'" && exit 1 )

all_books="bap/book_data/AUTO_books.txt"
test -f $all_books || ( echo "ERROR: Book list not found at ${all_books}" && exit 1 )

while read -r line; do
  repo=${line%%' '*}
  slug=${line##*' '}
  echo "running ./enki --data-dir ./data/$slug --command $arg_command --repo openstax/$repo --book-slug $slug --style default --ref main"
  ./enki --data-dir ./data/$slug --command $command --repo openstax/$repo --book-slug $slug --style default --ref main
done <$all_books
