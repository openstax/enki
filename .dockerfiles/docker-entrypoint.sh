#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

say() { echo -e "$1"; }
# https://stackoverflow.com/a/25515370
yell() { >&2 say "$0: ${c_red}$*${c_none}"; }
die() {
  yell "$1"
  exit 112
}
try() { "$@" || die "${c_red}ERROR: could not run [$*]${c_none}" 112; }

data_dir="/data"
fetched_dir="${data_dir}/raw"
assembled_dir="${data_dir}/assembled"

step_name=$1

case $step_name in
    fetch)
        collection_id=$2
        book_server=cnx.org
        book_version=latest
        book_slugs_url='https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json'

        # Validate commandline arguments
        [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."

        # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/fetch-book.js#L38
        yes | try neb get -r -d "${fetched_dir}" "${book_server}" "${collection_id}" "${book_version}" || die "failed to fetch from server."
        try wget "${book_slugs_url}" -O "${fetched_dir}/approved-book-list.json"
    ;;
    assemble)

        try neb assemble "${fetched_dir}" "${assembled_dir}"
    ;;
    *) # All other arguments are an error
        die "Invalid command. The first argument needs to be a command like 'fetch'"
        shift
    ;;
esac

# exec "$@"
