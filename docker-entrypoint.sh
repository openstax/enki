#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# Activate the python virtualenv
source /opt/venv/bin/activate

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
book_dir="${data_dir}/assembled"


function do_step() {
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
            try wget "${book_slugs_url}" -O "${b}/approved-book-list.json"
        ;;
        assemble)
            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/assemble-book.js
            try neb assemble "${fetched_dir}" "${book_dir}"
        ;;
        assemble-metadata)
            target_dir=$book_dir
            echo "{" > $book_dir/uuid-to-revised-map.json
            find $fetched_dir/ -path */m*/metadata.json | xargs cat | jq -r '. | "\"\(.id)\": \"\(.revised)\","' >> $book_dir/uuid-to-revised-map.json
            echo '"dummy": "dummy"' >> $book_dir/uuid-to-revised-map.json
            echo "}" >> $book_dir/uuid-to-revised-map.json

            assemble-meta "$book_dir/collection.assembled.xhtml" $book_dir/uuid-to-revised-map.json "$target_dir/collection.assembled-metadata.json"
            rm $book_dir/uuid-to-revised-map.json
        ;;
        link-extras)
            book_server=archive.cnx.org
            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/link-extras.js#L40
            try python3 /bakery-scripts/scripts/link_extras.py "${book_dir}" "${book_server}" /bakery-scripts/scripts/canonical-book-list.json
        ;;
        bake)
            recipe_name=$2

            # Validate commandline arguments
            [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."

            try /recipes/bake_root -b "${recipe_name}" -r /cnx-recipes-recipes-output/ -i "${book_dir}/collection.linked.xhtml" -o "${book_dir}/collection.baked.xhtml"

            style_file="/cnx-recipes-styles-output/${recipe_name}-pdf.css"

            [[ -f "${style_file}" ]] || yell "Warning: Could not find style file for recipe name '${recipe_name}'"

            if [ -f "${style_file}" ]
            then
                cp "${style_file}" "${book_dir}"
                sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename ${style_file})\" />&%" "${book_dir}/collection.baked.xhtml"
            fi
        ;;
        mathify)
            # Remove the mathified file if it already exists ecause the code assumes the file does not exist
            [[ -f "${book_dir}/collection.mathified.xhtml" ]] && rm "${book_dir}/collection.mathified.xhtml"

            try node /mathify/typeset/start.js -i "${book_dir}/collection.baked.xhtml" -o "${book_dir}/collection.mathified.xhtml" -f svg 
        ;;
        pdf)
            try prince -v --output="${book_dir}/collection.pdf" "${book_dir}/collection.mathified.xhtml"
        ;;

        bake-metadata)
            # TODO: Use a real collection id
            collection_id="fakecollectionid"
            book_metadata="${fetched_dir}/metadata.json"
            book_uuid="$(cat $book_metadata | jq -r '.id')"
            book_version="$(cat $book_metadata | jq -r '.version')"
            book_legacy_id="$(cat $book_metadata | jq -r '.legacy_id')"
            book_legacy_version="$(cat $book_metadata | jq -r '.legacy_version')"
            book_ident_hash="$book_uuid@$book_version"
            book_license="$(cat $book_metadata | jq '.license')"
            target_dir="$book_dir"
            book_slugs_file="/tmp/book-slugs.json"
            cat "$fetched_dir/approved-book-list.json" | jq ".approved_books|map(.books)|flatten" > "$book_slugs_file"
            cat "$book_dir/collection.assembled-metadata.json" | \
                jq --arg ident_hash "$book_ident_hash" --arg uuid "$book_uuid" --arg version "$book_version" --argjson license "$book_license" \
                --arg legacy_id "$book_legacy_id" --arg legacy_version "$book_legacy_version" \
                '. + {($ident_hash): {id: $uuid, version: $version, license: $license, legacy_id: $legacy_id, legacy_version: $legacy_version}}' > "/tmp/collection.baked-input-metadata.json"
            bake-meta /tmp/collection.baked-input-metadata.json "$target_dir/collection.baked.xhtml" "$book_uuid" "$book_slugs_file" "$target_dir/collection.baked-metadata.json"
        ;;
        checksum)
            try checksum "$book_dir" "$book_dir"
        ;;
        disassemble)
            try disassemble "$book_dir/collection.baked.xhtml" "$book_dir/collection.baked-metadata.json" "collection" "$book_dir"
        ;;
        patch-disassembled-links)
            target_dir="$book_dir"
            try patch-same-book-links "$book_dir" "$target_dir" "collection"
        ;;
        jsonify)
            target_dir="$book_dir"
            try jsonify "$book_dir" "$target_dir"
            try jsonschema -i "$target_dir/collection.toc.json" /bakery-scripts/scripts/book-schema.json
            for jsonfile in "$target_dir/"*@*.json; do
                #ignore -metadata.json files
                if [[ $jsonfile != *-metadata.json ]]; then
                    try jsonschema -i "$jsonfile" /bakery-scripts/scripts/page-schema.json
                fi
            done
        ;;
        validate-xhtml)
            for xhtmlfile in $(find $book_dir -name '*.xhtml')
            do
                java -cp /xhtml-validator/xhtml-validator.jar org.openstax.xml.Main "$xhtmlfile" duplicate-id broken-link
            done
        ;;

        shell | /bin/bash)
            bash
        ;;
        *) # All other arguments are an error
            die "Invalid command. The first argument needs to be a command like 'fetch'. Instead, it was '${step_name}'"
            shift
        ;;
    esac
}

function do_step_named() {
    step_name=$1
    say "==> Starting ${step_name}"
    do_step $@
    say "==> Ending ${step_name}"
}


collection_id=$2
recipe_name=$3
case $1 in
    all-pdf)
        [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."
        do_step_named fetch ${collection_id}
        do_step_named assemble
        do_step_named link-extras
        do_step_named bake ${recipe_name}
        do_step_named mathify
        do_step_named pdf
    ;;
    all-web)
        [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."
        do_step_named fetch ${collection_id}
        do_step_named assemble
        do_step_named assemble-metadata
        do_step_named link-extras
        do_step_named bake ${recipe_name}
        do_step_named bake-metadata
        do_step_named checksum
        do_step_named disassemble
        do_step_named patch-disassembled-links
        do_step_named jsonify
        do_step_named validate-xhtml
    ;;
    *) # Assume the user is only running one step
        do_step $@
    ;;
esac
