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
                try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename ${style_file})\" />&%" "${book_dir}/collection.baked.xhtml"
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
            try bake-meta /tmp/collection.baked-input-metadata.json "$target_dir/collection.baked.xhtml" "$book_uuid" "$book_slugs_file" "$target_dir/collection.baked-metadata.json"
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
                try java -cp /xhtml-validator/xhtml-validator.jar org.openstax.xml.Main "$xhtmlfile" duplicate-id broken-link
            done
        ;;


        git-fetch)
            # Environment variables:
            # - COMMON_LOG_DIR
            # - GH_SECRET_CREDS
            # - CONTENT_OUTPUT
            # - BOOK_INPUT (deleteme)
            # - UNUSED_RESOURCE_OUTPUT
            # - book_dir
            #
            # Arguments:
            # 1. repo_name
            # 2. git_ref
            # 3. slug_name
            check_output_dir "${git_fetched_dir}"

            [[ ${COMMON_LOG_DIR} != '' ]] && exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

            repo_name=$2
            git_ref=$3
            slug_name=$4

            [[ "${git_ref}" == latest ]] && git_ref=main
            [[ "${repo_name}" == */* ]] || repo_name="openstax/${repo_name}"

            remote_url="https://github.com/${repo_name}.git"
            
            # Do not show creds
            set +x
            if [[ ${GH_SECRET_CREDS} != '' ]]; then
                creds_dir=tmp-gh-creds
                creds_file="$creds_dir/gh-creds"
                git config --global credential.helper "store --file=$creds_file"
                mkdir "$creds_dir"
                set +x
                # Do not show creds
                echo "https://$GH_SECRET_CREDS@github.com" > "$creds_file" 2>&1
            fi
            set -x
            

            # If git_ref starts with '@' then it is a commit and check out the individual commit
            # Or, https://stackoverflow.com/a/7662531
            [[ ${git_ref} =~ ^[a-f0-9]{40}$ ]] && git_ref="@${git_ref}"

            if [[ ${git_ref} = @* ]]; then
                git_commit="${git_ref:1}"
                GIT_TERMINAL_PROMPT=0 git clone --depth 50 "${remote_url}" "${git_fetched_dir}"
                pushd "${git_fetched_dir}"
                git reset --hard "${git_commit}"
                # If the commit was not recent, try cloning the whole repo
                if [[ $? != 0 ]]; then
                    popd
                    GIT_TERMINAL_PROMPT=0 try git clone "${remote_url}" "${git_fetched_dir}"
                    pushd "${git_fetched_dir}"
                    git reset --hard "${git_commit}"
                fi
                popd
            else
                GIT_TERMINAL_PROMPT=0 try git clone --depth 1 "${remote_url}" --branch "${git_ref}" "${git_fetched_dir}"
            fi

            if [[ ! -f "${git_fetched_dir}/collections/${slug_name}.collection.xml" ]]; then
                echo "No matching book for slug in this repo"
                exit 1
            fi
        ;;

        git-fetch-meta)
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
            check_input_dir "${git_fetched_dir}"
            check_output_dir "${git_assembled_dir}"
            
            shopt -s globstar nullglob
            for collection in "${git_fetched_dir}/collections/"*; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                # if [[ -n "${TARGET_BOOK}" ]]; then
                #     if [[ "$slug_name" != "${TARGET_BOOK}" ]]; then
                #         continue
                #     fi
                # fi
                try cp "$collection" "${git_fetched_dir}/modules/collection.xml"

                try neb assemble "${git_fetched_dir}/modules" temp-assembly/

                try cp "temp-assembly/collection.assembled.xhtml" "${git_assembled_dir}/$slug_name.assembled.xhtml"
                try rm -rf temp-assembly
                try rm "${git_fetched_dir}/modules/collection.xml"
            done
            shopt -u globstar nullglob
        ;;

        git-assemble-meta)
            check_input_dir "${git_fetched_dir}"
            check_input_dir "${git_assembled_dir}"
            check_output_dir "${git_assembled_meta_dir}"

            shopt -s globstar nullglob
            # Create an empty map file for invoking assemble-meta
            echo "{}" > uuid-to-revised-map.json
            for collection in "${git_assembled_dir}/"*.assembled.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                # if [[ -n "${TARGET_BOOK}" ]]; then
                #     if [[ "$slug_name" != "${TARGET_BOOK}" ]]; then
                #         continue
                #     fi
                # fi
                try assemble-meta "${git_assembled_dir}/$slug_name.assembled.xhtml" uuid-to-revised-map.json "${git_assembled_meta_dir}/${slug_name}.assembled-metadata.json"
            done
            try rm uuid-to-revised-map.json
            shopt -u globstar nullglob
        ;;

        git-bake)
            recipe_name=$2
            check_input_dir "${git_assembled_dir}"
            check_output_dir "${git_baked_dir}"

            # FIXME: We assume that every book in the group uses the same style
            # This assumption will not hold true forever, and book style + recipe name should
            # be pulled from fetched-book-group (while still allowing injection w/ CLI)

            # FIXME: Style devs will probably not like having to bake multiple books repeatedly,
            # especially since they shouldn't care about link-extras correctness during their
            # work cycle.

            # FIXME: Separate style injection step from baking step. This is way too much work to change a line injected into the head tag
            style_file="/cnx-recipes-styles-output/${recipe_name}-pdf.css"

            if [[ -f "$style_file" ]]
                then
                    cp "$style_file" "${git_baked_output}"
                    cp "$style_file" "${STYLE_OUTPUT}"
                else
                    echo "Warning: Style Not Found" > "${git_baked_output}/stderr"
            fi

            shopt -s globstar nullglob
            for collection in "${git_assembled_dir}/"*.assembled.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                # if [[ -n "${TARGET_BOOK}" ]]; then
                #     if [[ "$slug_name" != "${TARGET_BOOK}" ]]; then
                #         continue
                #     fi
                # fi
                /recipes/bake_root -b "${recipe_name}" -r cnx-recipes-output/rootfs/recipes -i "${ASSEMBLED_INPUT}/$slug_name.assembled.xhtml" -o "${BAKED_OUTPUT}/$slug_name.baked.xhtml"
                if [[ -f "$style_file" ]]
                    then
                        sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename "$style_file")\" />&%" "${BAKED_OUTPUT}/$slug_name.baked.xhtml"
                fi
            done
            shopt -u globstar nullglob

        ;;

        git-bake-meta)
        ;;

        git-link)
        ;;

        git--meta)
        ;;

        git-disassemble)
        ;;

        git-patch-disassembled-links)
        ;;

        git-jsonify)
        ;;

        git-validate-xhtml)
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


case $1 in
    all-pdf)
        collection_id=$2
        recipe_name=$3
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
        collection_id=$2
        recipe_name=$3
        [[ ${collection_id} ]] || die "A collection id is missing. It is necessary for fetching a book from archive."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."

        do_step_named fetch ${collection_id}
        do_step_named fetch-meta
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
    all-git-web)
        set -x
        repo_name=$2
        git_ref=$3
        slug_name=$4
        recipe_name=$5
        [[ ${repo_name} ]] || die "A repository name is missing. It is necessary for baking a book."
        [[ ${git_ref} ]] || die "A git ref (branch or tag or @commit) is missing. It is necessary for baking a book."
        [[ ${slug_name} ]] || die "A slug name is missing. It is necessary for baking a book."
        [[ ${recipe_name} ]] || die "A recipe name is missing. It is necessary for baking a book."

        do_step_named git-fetch ${repo_name} ${git_ref} ${slug_name}
        do_step_named git-fetch-meta
        do_step_named git-assemble
        do_step_named git-assemble-meta
        do_step_named git-bake ${recipe_name}
        # do_step_named git-bake-meta
        # do_step_named git-link
        # do_step_named git--meta
        # do_step_named git-disassemble
        # do_step_named git-patch-disassembled-links
        # do_step_named git-jsonify
        # do_step_named git-validate-xhtml
    ;;
    *) # Assume the user is only running one step
        do_step $@
    ;;
esac
