#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# https://stackoverflow.com/questions/5947742/how-to-change-the-output-color-of-echo-in-linux
if [[ $(tput colors) -ge 8 ]]; then
  declare -x c_red=$(tput setaf 1)
  declare -x c_none=$(tput sgr0) # Keep this last so TRACE=true does not cause everything to be cyan
fi

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
        book_version=latest
        book_server=cnx.org
        book_slugs_url='https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json'

        # Validate commandline arguments
        [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."

        # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/fetch-book.js#L38
        yes | try neb get -r -d "${fetched_dir}" "${book_server}" "${collection_id}" "${book_version}" || die "failed to fetch from server."
        try wget "${book_slugs_url}" -O "${fetched_dir}/approved-book-list.json"
    ;;
    assemble)
        # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/assemble-book.js
        try neb assemble "${fetched_dir}" "${assembled_dir}"
    ;;
    link-extras)
        book_server=archive.cnx.org
        # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/link-extras.js#L40
        try python3 /bakery-scripts/scripts/link_extras.py "${assembled_dir}" "${book_server}" /bakery-scripts/scripts/canonical-book-list.json
    ;;
    bake)
        recipe_name=$2

        # Validate commandline arguments
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."

        try /recipes/bake_root -b "${recipe_name}" -r /cnx-recipes-recipes-output/ -i "${assembled_dir}/collection.linked.xhtml" -o "${assembled_dir}/collection.baked.xhtml"

        style_file="/cnx-recipes-styles-output/${recipe_name}-pdf.css"

        [[ -f "${style_file}" ]] || yell "Warning: Could not find style file for recipe name '${recipe_name}'"

        if [ -f "${style_file}" ]
        then
            cp "${style_file}" "${assembled_dir}"
            sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename ${style_file})\" />&%" "${assembled_dir}/collection.baked.xhtml"
        fi
    ;;
    mathify)
        # Remove the mathified file if it already exists ecause the code assumes the file does not exist
        [[ -f "${assembled_dir}/collection.mathified.xhtml" ]] && rm "${assembled_dir}/collection.mathified.xhtml"

        try node /mathify/typeset/start.js -i "${assembled_dir}/collection.baked.xhtml" -o "${assembled_dir}/collection.mathified.xhtml" -f svg 
    ;;
    pdf)
        try prince -v --output="${assembled_dir}/collection.pdf" "${assembled_dir}/collection.mathified.xhtml"
    ;;
    shell | /bin/bash)
        bash
    ;;
    *) # All other arguments are an error
        die "Invalid command. The first argument needs to be a command like 'fetch'"
        shift
    ;;
esac

# exec "$@"
