#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# Trace and log if TRACE_ON is set
[[ ${TRACE_ON} ]] && set -x && exec > >(tee /data/log >&2) 2>&1


# Activate the python virtualenv
source /openstax/venv/bin/activate

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
jsonified_dir="${data_dir}/jsonified"
upload_dir="${data_dir}/upload"


git_resources_dir="${data_dir}/resources/"
git_unused_dir="${data_dir}/unused-resources/"
git_fetched_dir="${data_dir}/fetched-book-group/"
git_assembled_dir="${data_dir}/assembled-book-group/"
git_assembled_meta_dir="${data_dir}/assembled-metadata-group/"
git_baked_dir="${data_dir}/baked-book-group/"
git_baked_meta_dir="${data_dir}/baked-metadata-group/"
git_linked_dir="${data_dir}/linked-single/"
git_mathified_dir="${data_dir}/mathified-single/"
git_disassembled_dir="${data_dir}/disassembled-single/"
git_artifacts_dir="${data_dir}/artifacts-single/"
git_disassembled_linked_dir="${data_dir}/disassembled-linked-single/"
git_jsonified_dir="${data_dir}/jsonified-single/"


function check_input_dir() {
    [[ -d $1 ]] || die "Expected directory to exist but it was missing. Maybe an earlier step needs to run: '$1'"
}
function check_output_dir() {
    [[ $1 ]] || die "This output directory name is not set (it is an empty string)"
    [[ -d $1 ]] || try mkdir -p $1
}

function do_step() {
    step_name=$1

    case $step_name in
        archive-fetch)
            collection_id=$2
            book_version=latest
            book_server=cnx.org

            # Validate commandline arguments
            [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."

            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/fetch-book.js#L38
            yes | try neb get -r -d "${fetched_dir}" "${book_server}" "${collection_id}" "${book_version}"
        ;;
        archive-fetch-metadata)
            book_slugs_url='https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json'
            try wget "${book_slugs_url}" -O "${fetched_dir}/approved-book-list.json"
        ;;
        archive-assemble)
            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/assemble-book.js
            try neb assemble "${fetched_dir}" "${book_dir}"
        ;;
        archive-assemble-metadata)
            target_dir=$book_dir
            echo "{" > $book_dir/uuid-to-revised-map.json
            find $fetched_dir/ -path */m*/metadata.json | xargs cat | jq -r '. | "\"\(.id)\": \"\(.revised)\","' >> $book_dir/uuid-to-revised-map.json
            echo '"dummy": "dummy"' >> $book_dir/uuid-to-revised-map.json
            echo "}" >> $book_dir/uuid-to-revised-map.json

            assemble-meta "$book_dir/collection.assembled.xhtml" $book_dir/uuid-to-revised-map.json "$target_dir/collection.assembled-metadata.json"
            rm $book_dir/uuid-to-revised-map.json
        ;;
        archive-link-extras)
            book_server=archive.cnx.org
            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/link-extras.js#L40
            try python3 /openstax/bakery-scripts/scripts/link_extras.py "${book_dir}" "${book_server}" /openstax/bakery-scripts/scripts/canonical-book-list.json
        ;;
        archive-bake)
            recipe_name=$2

            # Validate commandline arguments
            [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."

            try /openstax/recipes/bake_root -b "${recipe_name}" -r /openstax/cnx-recipes-recipes-output/ -i "${book_dir}/collection.linked.xhtml" -o "${book_dir}/collection.baked.xhtml"

            style_file="/openstax/cnx-recipes-styles-output/${recipe_name}-pdf.css"

            [[ -f "${style_file}" ]] || yell "Warning: Could not find style file for recipe name '${recipe_name}'"

            if [ -f "${style_file}" ]
            then
                cp "${style_file}" "${book_dir}"
                try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename ${style_file})\" />&%" "${book_dir}/collection.baked.xhtml"
            fi
        ;;
        archive-mathify)
            # Remove the mathified file if it already exists ecause the code assumes the file does not exist
            [[ -f "${book_dir}/collection.mathified.xhtml" ]] && rm "${book_dir}/collection.mathified.xhtml"

            try node /openstax/mathify/typeset/start.js -i "${book_dir}/collection.baked.xhtml" -o "${book_dir}/collection.mathified.xhtml" -f svg 
        ;;
        archive-pdf)
            try prince -v --output="${book_dir}/collection.pdf" "${book_dir}/collection.mathified.xhtml"
        ;;

        archive-bake-metadata)
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
            try bake-meta /tmp/collection.baked-input-metadata.json "$target_dir/collection.baked.xhtml" "$book_uuid" "$book_slugs_file" "$target_dir/collection.baked-metadata.json"
        ;;
        archive-checksum)
            try checksum "$book_dir" "$book_dir"
        ;;
        archive-disassemble)
            try disassemble "$book_dir/collection.baked.xhtml" "$book_dir/collection.baked-metadata.json" "collection" "$book_dir"
        ;;
        archive-patch-disassembled-links)
            target_dir="$book_dir"
            try patch-same-book-links "$book_dir" "$target_dir" "collection"
        ;;
        archive-jsonify)
            target_dir="$jsonified_dir"
            
            try mkdir -p $target_dir
            try jsonify "$book_dir" "$target_dir"
            try jsonschema -i "$target_dir/collection.toc.json" /openstax/bakery-scripts/scripts/book-schema.json
            for jsonfile in "$target_dir/"*@*.json; do
                #ignore -metadata.json files
                if [[ $jsonfile != *-metadata.json ]]; then
                    try jsonschema -i "$jsonfile" /openstax/bakery-scripts/scripts/page-schema.json
                fi
            done
        ;;
        archive-validate-xhtml)
            for xhtmlfile in $(find $jsonified_dir -name '*@*.xhtml')
            do
                try java -cp /openstax/xhtml-validator/xhtml-validator.jar org.openstax.xml.Main "$xhtmlfile" duplicate-id broken-link
            done
        ;;
        archive-upload-book)
            s3_bucket_name=$2
            code_version=$3
            s3_bucket_prefix="apps/archive/${code_version}"

            [[ ${s3_bucket_name} ]] || die "An S3 bucket name is missing. It is necessary for uploading"
            [[ ${code_version} ]] || die "A code version is missing. It is necessary for uploading"

            [[ "${AWS_ACCESS_KEY_ID}" != '' ]] || die "AWS_ACCESS_KEY_ID environment variable is missing. It is necessary for uploading"
            [[ "${AWS_SECRET_ACCESS_KEY}" != '' ]] || die "AWS_SECRET_ACCESS_KEY environment variable is missing. It is necessary for uploading"

            book_metadata="${fetched_dir}/metadata.json"
            resources_dir="${book_dir}/resources"
            target_dir="${upload_dir}/contents"
            mkdir -p "$target_dir"
            book_uuid="$(cat $book_metadata | jq -r '.id')"
            book_version="$(cat $book_metadata | jq -r '.version')"

            for jsonfile in "$jsonified_dir/"*@*.json; do try cp "$jsonfile" "$target_dir/$(basename $jsonfile)"; done;
            for xhtmlfile in "$jsonified_dir/"*@*.xhtml; do try cp "$xhtmlfile" "$target_dir/$(basename $xhtmlfile)"; done;
            try aws s3 cp --recursive "$target_dir" "s3://${s3_bucket_name}/${s3_bucket_prefix}/contents"
            try copy-resources-s3 "$resources_dir" "${s3_bucket_name}" "${s3_bucket_prefix}/resources"

            #######################################
            # UPLOAD BOOK LEVEL FILES LAST
            # so that if an error is encountered
            # on prior upload steps, those files
            # will not be found by watchers
            #######################################
            toc_s3_link_json="s3://${s3_bucket_name}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.json"
            toc_s3_link_xhtml="s3://${s3_bucket_name}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.xhtml"
            try aws s3 cp "$book_dir/collection.toc.json" "$toc_s3_link_json"
            try aws s3 cp "$book_dir/collection.toc.xhtml" "$toc_s3_link_xhtml"

            echo "DONE: See book at ${toc_s3_link_json} and ${toc_s3_link_xhtml}"
        ;;


        git-fetch)
            check_output_dir "${git_fetched_dir}"

            repo_name=$2
            git_ref=$3
            target_slug_name=$4

            [[ ${repo_name} ]] || die "A repo name is missing"
            [[ ${git_ref} ]] || die "A git reference is missing (branch, tag, or @commit)"
            [[ ${target_slug_name} ]] || die "A book slug name is missing"

            [[ "${git_ref}" == latest ]] && git_ref=main
            [[ "${repo_name}" == */* ]] || repo_name="openstax/${repo_name}"

            remote_url="https://github.com/${repo_name}.git"
            
            if [[ ${GH_SECRET_CREDS} ]]; then
                creds_dir=tmp-gh-creds
                creds_file="$creds_dir/gh-creds"
                git config --global credential.helper "store --file=$creds_file"
                mkdir "$creds_dir"
                # Do not show creds
                echo "https://$GH_SECRET_CREDS@github.com" > "$creds_file" 2>&1
            fi

            # If git_ref starts with '@' then it is a commit and check out the individual commit
            # Or, https://stackoverflow.com/a/7662531
            [[ ${git_ref} =~ ^[a-f0-9]{40}$ ]] && git_ref="@${git_ref}"

            if [[ ${git_ref} = @* ]]; then
                git_commit="${git_ref:1}"
                GIT_TERMINAL_PROMPT=0 try git clone --depth 50 "${remote_url}" "${git_fetched_dir}"
                pushd "${git_fetched_dir}"
                try git reset --hard "${git_commit}"
                # If the commit was not recent, try cloning the whole repo
                if [[ $? != 0 ]]; then
                    popd
                    GIT_TERMINAL_PROMPT=0 try git clone "${remote_url}" "${git_fetched_dir}"
                    pushd "${git_fetched_dir}"
                    try git reset --hard "${git_commit}"
                fi
                popd
            else
                GIT_TERMINAL_PROMPT=0 try git clone --depth 1 "${remote_url}" --branch "${git_ref}" "${git_fetched_dir}"
            fi

            if [[ ! -f "${git_fetched_dir}/collections/${target_slug_name}.collection.xml" ]]; then
                echo "No matching book for slug in this repo"
                exit 1
            fi
        ;;

        git-fetch-metadata)
            check_input_dir "${git_fetched_dir}"
            check_output_dir "${git_fetched_dir}"
            check_output_dir "${git_resources_dir}"
            check_output_dir "${git_unused_dir}"

            
            try fetch-update-meta "${git_fetched_dir}/.git" "${git_fetched_dir}/modules" "${git_fetched_dir}/collections" "${git_ref}" "${git_fetched_dir}/canonical.json"
            try rm -rf "${git_fetched_dir}/.git"
            try rm -rf "$creds_dir"

            try fetch-map-resources "${git_fetched_dir}/modules" "${git_fetched_dir}/media" . "${git_unused_dir}"
            # Either the media is in resources or unused-resources, this folder should be empty (-d will fail otherwise)
            try rm -d "${git_fetched_dir}/media"
        ;;

        git-assemble)
            opt_only_one_book=$2
            check_input_dir "${git_fetched_dir}"
            check_output_dir "${git_assembled_dir}"
            
            shopt -s globstar nullglob
            for collection in "${git_fetched_dir}/collections/"*; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${opt_only_one_book}" ]]; then
                    if [[ "$slug_name" != "${opt_only_one_book}" ]]; then
                        continue
                    fi
                fi
                try cp "$collection" "${git_fetched_dir}/modules/collection.xml"

                try neb assemble "${git_fetched_dir}/modules" temp-assembly/

                try cp "temp-assembly/collection.assembled.xhtml" "${git_assembled_dir}/$slug_name.assembled.xhtml"
                try rm -rf temp-assembly
                try rm "${git_fetched_dir}/modules/collection.xml"
            done
            shopt -u globstar nullglob
        ;;

        git-assemble-meta)
            opt_only_one_book=$2
            check_input_dir "${git_fetched_dir}"
            check_input_dir "${git_assembled_dir}"
            check_output_dir "${git_assembled_meta_dir}"

            shopt -s globstar nullglob
            # Create an empty map file for invoking assemble-meta
            echo "{}" > uuid-to-revised-map.json
            for collection in "${git_assembled_dir}/"*.assembled.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${opt_only_one_book}" ]]; then
                    if [[ "$slug_name" != "${opt_only_one_book}" ]]; then
                        continue
                    fi
                fi
                try assemble-meta "${git_assembled_dir}/$slug_name.assembled.xhtml" uuid-to-revised-map.json "${git_assembled_meta_dir}/${slug_name}.assembled-metadata.json"
            done
            try rm uuid-to-revised-map.json
            shopt -u globstar nullglob
        ;;

        git-bake)
            recipe_name=$2
            opt_only_one_book=$3
            [[ ${recipe_name} ]] || die "A recipe name is missing"
            check_input_dir "${git_assembled_dir}"
            check_output_dir "${git_baked_dir}"

            # FIXME: We assume that every book in the group uses the same style
            # This assumption will not hold true forever, and book style + recipe name should
            # be pulled from fetched-book-group (while still allowing injection w/ CLI)

            # FIXME: Style devs will probably not like having to bake multiple books repeatedly,
            # especially since they shouldn't care about link-extras correctness during their
            # work cycle.

            # FIXME: Separate style injection step from baking step. This is way too much work to change a line injected into the head tag
            style_file="/openstax/cnx-recipes-styles-output/${recipe_name}-pdf.css"

            if [[ -f "$style_file" ]]
                then
                    try cp "$style_file" "${git_baked_dir}/the-style-pdf.css"
                else
                    echo "Warning: Style Not Found" > "${git_baked_dir}/stderr"
            fi

            shopt -s globstar nullglob
            for collection in "${git_assembled_dir}/"*.assembled.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${opt_only_one_book}" ]]; then
                    if [[ "$slug_name" != "${opt_only_one_book}" ]]; then
                        continue
                    fi
                fi
                try /openstax/recipes/bake_root -b "${recipe_name}" -r /openstax/cnx-recipes-recipes-output/ -i "${git_assembled_dir}/$slug_name.assembled.xhtml" -o "${git_baked_dir}/$slug_name.baked.xhtml"
                if [[ -f "$style_file" ]]
                    then
                        try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"the-style-pdf.css\" />&%" "${git_baked_dir}/$slug_name.baked.xhtml"
                fi
            done
            shopt -u globstar nullglob
        ;;

        git-bake-meta)
            opt_only_one_book=$2
            check_input_dir "${git_assembled_meta_dir}"
            check_input_dir "${git_baked_dir}"
            check_output_dir "${git_baked_meta_dir}"

            shopt -s globstar nullglob
            for collection in "${git_baked_dir}/"*.baked.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${opt_only_one_book}" ]]; then
                    if [[ "$slug_name" != "${opt_only_one_book}" ]]; then
                        continue
                    fi
                fi

                try bake-meta "${git_assembled_meta_dir}/$slug_name.assembled-metadata.json" "${git_baked_dir}/$slug_name.baked.xhtml" "" "" "${git_baked_meta_dir}/$slug_name.baked-metadata.json"
            done
            shopt -u globstar nullglob
        ;;

        git-link)
            target_slug_name=$2
            opt_only_one_book=$3
            [[ ${target_slug_name} ]] || die "An book slug name is missing"
            check_input_dir "${git_baked_dir}"
            check_input_dir "${git_baked_meta_dir}"
            check_output_dir "${git_linked_dir}"

            if [[ -n "${opt_only_one_book}" ]]; then
                try link-single "${git_baked_dir}" "${git_baked_meta_dir}" "${target_slug_name}" "${git_linked_dir}/${target_slug_name}.linked.xhtml" --mock-otherbook
            else
                try link-single "${git_baked_dir}" "${git_baked_meta_dir}" "${target_slug_name}" "${git_linked_dir}/${target_slug_name}.linked.xhtml"
            fi
        ;;

        git-disassemble)
            target_slug_name=$2
            [[ ${target_slug_name} ]] || die "An book slug name is missing"
            check_input_dir "${git_linked_dir}"
            check_input_dir "${git_baked_meta_dir}"
            check_output_dir "${git_disassembled_dir}"

            try disassemble "${git_linked_dir}/$target_slug_name.linked.xhtml" "${git_baked_meta_dir}/$target_slug_name.baked-metadata.json" "$target_slug_name" "${git_disassembled_dir}"
        ;;

        git-patch-disassembled-links)
            target_slug_name=$2
            [[ ${target_slug_name} ]] || die "An book slug name is missing"
            check_input_dir "${git_disassembled_dir}"
            check_output_dir "${git_disassembled_linked_dir}"

            try patch-same-book-links "${git_disassembled_dir}" "${git_disassembled_linked_dir}" "$target_slug_name"
            try cp "${git_disassembled_dir}"/*@*-metadata.json "${git_disassembled_linked_dir}"
            try cp "${git_disassembled_dir}"/"$target_slug_name".toc* "${git_disassembled_linked_dir}"
        ;;

        git-jsonify)
            target_slug_name=$2
            [[ ${target_slug_name} ]] || die "An book slug name is missing"
            check_input_dir "${git_disassembled_linked_dir}"
            check_output_dir "${git_jsonified_dir}"

            try jsonify "${git_disassembled_linked_dir}" "${git_jsonified_dir}"
            try jsonschema -i "${git_jsonified_dir}/${target_slug_name}.toc.json" /openstax/bakery-scripts/scripts/book-schema-git.json

            for jsonfile in "${git_jsonified_dir}/"*@*.json; do
                try jsonschema -i "$jsonfile" /openstax/bakery-scripts/scripts/page-schema.json
            done
        ;;

        git-validate-xhtml)
            check_input_dir "${git_disassembled_linked_dir}"

            for xhtmlfile in $(find ${git_disassembled_linked_dir} -name '*.xhtml')
            do
                say "XHTML-validating ${xhtmlfile}"
                try java -cp /openstax/xhtml-validator/xhtml-validator.jar org.openstax.xml.Main "$xhtmlfile" duplicate-id broken-link
            done
        ;;
        git-mathify)
            target_slug_name=$2
            [[ ${target_slug_name} ]] || die "A book slug name is missing"

            check_input_dir "${git_linked_dir}"
            check_input_dir "${git_baked_dir}"
            check_output_dir "${git_mathified_dir}"

            # Style needed because mathjax will size converted math according to surrounding text
            try cp "${git_baked_dir}/the-style-pdf.css" "${git_linked_dir}"
            try cp "${git_baked_dir}/the-style-pdf.css" "${git_mathified_dir}"
            try node /openstax/mathify/typeset/start.js -i "${git_linked_dir}/$target_slug_name.linked.xhtml" -o "${git_mathified_dir}/$target_slug_name.mathified.xhtml" -f svg
        ;;
        git-pdfify)
            target_slug_name=$2
            target_pdf_filename=$3

            [[ ${target_slug_name} ]] || die "A book slug name is missing"
            [[ ${target_pdf_filename} ]] || die "A target PDF filename name is missing"

            check_input_dir "${git_mathified_dir}"
            check_output_dir "${git_artifacts_dir}"

            try prince -v --output="${git_artifacts_dir}/${target_pdf_filename}" "${git_mathified_dir}/${target_slug_name}.mathified.xhtml"
        ;;
        git-pdfify-meta)
            s3_bucket_name=$2
            target_pdf_filename=$3
            check_output_dir "${git_artifacts_dir}"

            [[ ${s3_bucket_name} ]] || die "An S3 bucket name is missing"
            [[ ${target_pdf_filename} ]] || die "A target PDF filename name is missing"

            pdf_url="https://${s3_bucket_name}.s3.amazonaws.com/${target_pdf_filename}"
            try echo -n "${pdf_url}" > "${git_artifacts_dir}/pdf_url"

            echo "DONE: See book at ${pdf_url}"
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
    say "==> Starting: $*"
    do_step $@
    say "==> Finished: $*"
}


case $1 in
    all-archive-pdf)
        collection_id=$2
        recipe_name=$3
        [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."
        
        do_step_named archive-fetch ${collection_id}
        do_step_named archive-fetch-metadata
        do_step_named archive-assemble
        do_step_named archive-link-extras
        do_step_named archive-bake ${recipe_name}
        do_step_named archive-mathify
        do_step_named archive-pdf
    ;;
    all-archive-web)
        collection_id=$2
        recipe_name=$3
        [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."

        do_step_named archive-fetch ${collection_id}
        do_step_named archive-fetch-metadata
        do_step_named archive-assemble
        do_step_named archive-assemble-metadata
        do_step_named archive-link-extras
        do_step_named archive-bake ${recipe_name}
        do_step_named archive-bake-metadata
        do_step_named archive-checksum
        do_step_named archive-disassemble
        do_step_named archive-patch-disassembled-links
        do_step_named archive-jsonify
        do_step_named archive-validate-xhtml
        # do_step_named archive-upload-book ${s3_bucket_name} ${code_version}
    ;;
    all-git-web)
        repo_name=$2
        git_ref=$3
        recipe_name=$4
        target_slug_name=$5
        opt_only_one_book=$6

        [[ ${repo_name} ]] || die "A repository name is missing. It is necessary for baking a book."
        [[ ${git_ref} ]] || die "A git ref (branch or tag or @commit) is missing. It is necessary for baking a book."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."
        [[ ${target_slug_name} ]] || die "A slug name is missing. It is necessary for baking a book."

        # Change opt_only_one_book from a boolean to the name of the one book
        if [[ ${opt_only_one_book} ]]; then
            opt_only_one_book=${target_slug_name}
        fi

        do_step_named git-fetch ${repo_name} ${git_ref} ${target_slug_name}
        do_step_named git-fetch-metadata
        do_step_named git-assemble ${opt_only_one_book}
        do_step_named git-assemble-meta ${opt_only_one_book}
        do_step_named git-bake ${recipe_name} ${opt_only_one_book}
        do_step_named git-bake-meta ${opt_only_one_book}
        do_step_named git-link ${target_slug_name} ${opt_only_one_book}
        do_step_named git-disassemble ${target_slug_name}
        do_step_named git-patch-disassembled-links ${target_slug_name}
        do_step_named git-jsonify ${target_slug_name}
        do_step_named git-validate-xhtml
    ;;
    all-git-pdf)
        repo_name=$2
        git_ref=$3
        recipe_name=$4
        target_slug_name=$5
        target_pdf_filename=$6
        opt_only_one_book=$7

        [[ ${repo_name} ]] || die "A repository name is missing. It is necessary for baking a book."
        [[ ${git_ref} ]] || die "A git ref (branch or tag or @commit) is missing. It is necessary for baking a book."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."
        [[ ${target_slug_name} ]] || die "A slug name is missing. It is necessary for baking a book."

        [[ $target_pdf_filename ]] || target_pdf_filename='book.pdf'

        # Change opt_only_one_book from a boolean to the name of the one book
        if [[ ${opt_only_one_book} ]]; then
            opt_only_one_book=${target_slug_name}
        fi

        do_step_named git-fetch ${repo_name} ${git_ref} ${target_slug_name}
        do_step_named git-fetch-metadata
        do_step_named git-assemble ${opt_only_one_book}
        do_step_named git-assemble-meta ${opt_only_one_book}
        do_step_named git-bake ${recipe_name} ${opt_only_one_book}
        do_step_named git-bake-meta ${opt_only_one_book}
        do_step_named git-link ${target_slug_name} ${opt_only_one_book}
        
        do_step_named git-mathify ${target_slug_name}
        do_step_named git-pdfify ${target_slug_name} ${target_pdf_filename}
    ;;
    *) # Assume the user is only running one step
        do_step $@
    ;;
esac

# Ensure the permissions of files are set to the host user/group, not root
# Other options: https://stackoverflow.com/a/53915137
try chown -R "$(stat -c '%u:%g' /data)" /data
