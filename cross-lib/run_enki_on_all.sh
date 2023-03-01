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

[[ $arg_command ]] || ( echo "ERROR: A command was not provided. Typical examples are 'all-git-pdf' or 'all-git-web' or 'all-git-epub'" && exit 1 )

all_books="cross-lib/book_data/AUTO_books.txt"
test -f $all_books || ( echo "ERROR: Book list not found at ${all_books}" && exit 1 )

mkdir -p cross-lib/logs/

# https://stackoverflow.com/a/20983251
echo_green() { echo -e "$(tput setaf 2)$*$(tput sgr0)"; }
echo_red() { echo -e "$(tput setaf 1)$*$(tput sgr0)"; }

run_and_log_enki () {
  echo "  running command $1 on $2 $3"
  start_time=$(date +%s)
  ./enki --data-dir ./data/$3-$1 --command $1 --repo openstax/$2 --book-slug $3 --style default --ref main &> cross-lib/logs/$2-$3.txt
  exit=$?
  stop_time=$(date +%s)
  elapsed_formatted="$(date -u -r $(($stop_time - $start_time)) +%T)"
  echo "  time to build $elapsed_formatted"
  if [ $exit == 0 ]; then
    echo_green "==> SUCCESS: $2 $3"
  else
    echo_red "==> FAILED with $exit: $2 $3"
  fi
}

while read -r line; do
  repo=${line%%' '*}
  slug=${line##*' '}
  # https://stackoverflow.com/a/35208546
  echo "" | run_and_log_enki $arg_command $repo $slug || true
done <$all_books

# final time report (& failures?)
