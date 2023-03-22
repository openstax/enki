#!/bin/bash

set -e

trap 'exit 1' INT

# Setup
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

all_books="cross-lib/book-data/AUTO_books.txt"
test -f $all_books || ( echo "ERROR: Book list not found at ${all_books}" && exit 1 )

mkdir -p cross-lib/logs/

# Helpers
# https://stackoverflow.com/a/20983251
echo_green() { echo -e "$(tput setaf 2)$*$(tput sgr0)"; }
echo_red() { echo -e "$(tput setaf 1)$*$(tput sgr0)"; }

format_time() {
  if [[ $(uname -s) = "Darwin" ]]; then 
    echo "$(date -u -r $1 +%T)"
  elif [[ $(uname -s) = "Linux" ]]; then
    echo "$(date --date="$1" +%H:%M:%S)"
  else
    echo "WARNING: Unrecognized operating system. Unable to format datetime."
  fi
}

# Nicely handle an enki run
run_and_log_enki () {
  echo "  running command $1 on $2 $3"
  start_time=$(date +%s)
  ./enki --data-dir ./data/$3-$1 --command $1 --repo openstax/$2 --book-slug $3 --style default --ref main &> cross-lib/logs/$repo-$slug.txt
  exit=$?
  stop_time=$(date +%s)
  elapsed_formatted=$( format_time $(($stop_time-$start_time)) )
  echo "  time to build $elapsed_formatted"
  if [ $exit == 0 ]; then
    echo_green "==> SUCCESS: $2 $3"
  else
    echo_red "==> FAILED with $exit: $2 $3"
  fi
  return $exit
}

# Read book list & collect data on runs
total_start=$(date +%s)
failed_count=0
success_count=0
while read -r line; do
  repo=${line%%' '*}
  slug=${line##*' '}
  # https://stackoverflow.com/a/35208546
  echo "" | run_and_log_enki $arg_command $repo $slug \
    && success_count=$(($success_count+1)) || failed_count=$(($failed_count+1))
done < <(cat "$all_books")
total_end=$(date +%s)
elapsed_formatted=$( format_time $(($total_end-$total_start)) )

# Final report:
echo "
Yeehaw! You've built E V E R Y T H I N G. Total runtime was $elapsed_formatted
Successes $success_count failures $failed_count
"
