#!/usr/bin/env bash

# This is run every time the docker container starts up.

set -e

# Trace and log if TRACE_ON is set
[[ ${TRACE_ON} ]] && set -x && export PS4='+ [${BASH_SOURCE##*/}:${LINENO}] '


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

source /openstax/venv/bin/activate

function ensure_arg() {
    local arg_name
    local pointer
    local value
    arg_name=$1
    message=${2:-"Environment variable '$arg_name' is missing. Set it"}
    pointer=$arg_name # https://stackoverflow.com/a/55331060
    value="${!pointer}"
    [[ $value ]] || die "$message"
}

function check_input_dir() {
    [[ -d $1 ]] || die "Expected directory to exist but it was missing. Maybe an earlier step needs to run: '$1'"
}
function check_output_dir() {
    [[ $1 ]] || die "This output directory name is not set (it is an empty string)"
    # Auto-create directories only in local dev mode. In Concourse Pipelines these directories should already exist.
    if [[ $1 =~ ^\/data && ! -d $1 ]]; then
        try mkdir -p $1
    fi
    [[ -d $1 ]] || die "Expected output directory to exist but it was missing. it needs to be added to the concourse job: '$1'"
}

function parse_book_dir() {
    check_input_dir $IO_BOOK

    ARG_RECIPE_NAME="$(cat $IO_BOOK/style)"
    ARG_TARGET_PDF_FILENAME="$(cat $IO_BOOK/pdf_filename)"

    [[ -f $IO_BOOK/collection_id ]] && ARG_COLLECTION_ID="$(cat $IO_BOOK/collection_id)"
    [[ -f $IO_BOOK/server ]] && ARG_ARCHIVE_SERVER="$(cat $IO_BOOK/server)"
    [[ -f $IO_BOOK/server_shortname ]] && ARG_ARCHIVE_SHORTNAME="$(cat $IO_BOOK/server_shortname)"
    ARG_COLLECTION_VERSION="$(cat $IO_BOOK/version)"

    [[ -f $IO_BOOK/repo ]] && ARG_REPO_NAME="$(cat $IO_BOOK/repo)"
    [[ -f $IO_BOOK/slug ]] && ARG_TARGET_SLUG_NAME="$(cat $IO_BOOK/slug)"
    ARG_GIT_REF="$(cat $IO_BOOK/version)"
}

# Concourse-CI runs each step in a separate process so parse_book_dir() needs to
# reset between each step
function unset_book_vars() {
    unset ARG_RECIPE_NAME
    unset ARG_TARGET_PDF_FILENAME
    unset ARG_COLLECTION_ID
    unset ARG_ARCHIVE_SERVER
    unset ARG_ARCHIVE_SHORTNAME
    unset ARG_COLLECTION_VERSION
    unset ARG_REPO_NAME
    unset ARG_TARGET_SLUG_NAME
    unset ARG_GIT_REF
}

function do_step() {
    step_name=$1

    case $step_name in
        local-create-book-directory)
            # This step is normally done by the concourse resource but for local development it is done here

            collection_id=$2 # repo name or collection id
            recipe=$3
            version=$4 # repo branch/tag/commit or archive collection version
            archive_server=${5:-cnx.org}

            ensure_arg collection_id 'Specify repo name (or archive collection id)'
            ensure_arg recipe 'Specify recipe name'
            ensure_arg version 'Specify repo/branch/tag/commit or archive collection version (e.g. latest)'
            ensure_arg archive_server 'Specify archive server (e.g. cnx.org)'

            [[ -d $INPUT_SOURCE_DIR ]] || mkdir $INPUT_SOURCE_DIR

            check_output_dir $INPUT_SOURCE_DIR

            # Write out the files
            echo "$collection_id" > $INPUT_SOURCE_DIR/collection_id
            echo "$recipe" > $INPUT_SOURCE_DIR/collection_style
            echo "$version" > $INPUT_SOURCE_DIR/version
            echo "$archive_server" > $INPUT_SOURCE_DIR/content_server
            # Dummy files
            echo '-123456' > $INPUT_SOURCE_DIR/id # job_id
            echo '{"content_server":{"name":"not_a_real_job_json_file"}}' > $INPUT_SOURCE_DIR/job.json
        ;;
        archive-look-up-book)
            ensure_arg INPUT_SOURCE_DIR

            check_input_dir $INPUT_SOURCE_DIR
            check_output_dir $IO_BOOK
            
            tail $INPUT_SOURCE_DIR/*
            cp $INPUT_SOURCE_DIR/id $IO_BOOK/job_id
            cp $INPUT_SOURCE_DIR/version $IO_BOOK/version
            cp $INPUT_SOURCE_DIR/collection_style $IO_BOOK/style

            cp $INPUT_SOURCE_DIR/collection_id $IO_BOOK/collection_id
            cp $INPUT_SOURCE_DIR/content_server $IO_BOOK/server

            server_shortname="$(cat $INPUT_SOURCE_DIR/job.json | jq -r '.content_server.name')"
            echo "$server_shortname" >$IO_BOOK/server_shortname
            pdf_filename="$(cat $IO_BOOK/collection_id)-$(cat $IO_BOOK/version)-$(cat $IO_BOOK/server_shortname)-$(cat $IO_BOOK/job_id).pdf"
            echo "$pdf_filename" > $IO_BOOK/pdf_filename
        ;;
        git-look-up-book)
            ensure_arg INPUT_SOURCE_DIR

            check_input_dir $INPUT_SOURCE_DIR
            check_output_dir $IO_BOOK

            tail $INPUT_SOURCE_DIR/*
            cp $INPUT_SOURCE_DIR/id $IO_BOOK/job_id
            cp $INPUT_SOURCE_DIR/version $IO_BOOK/version
            cp $INPUT_SOURCE_DIR/collection_style $IO_BOOK/style

            if [[ $(cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $3 }') ]]; then
                cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $1 "/" $2 }' > $IO_BOOK/repo
                cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $3 }' | sed 's/ *$//' > $IO_BOOK/slug
            else
                cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $1 }' > $IO_BOOK/repo
                cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $2 }' | sed 's/ *$//' > $IO_BOOK/slug
            fi
            pdf_filename="$(cat $IO_BOOK/slug)-$(cat $IO_BOOK/version)-git-$(cat $IO_BOOK/job_id).pdf"
            echo "$pdf_filename" > $IO_BOOK/pdf_filename
        ;;
        archive-dequeue-book)
            ensure_arg S3_QUEUE
            ensure_arg ARG_CODE_VERSION
            check_input_dir $IO_BOOK
            check_output_dir $IO_BOOK

            CONTENT_SOURCE=archive

            exec 2> >(tee $IO_BOOK/stderr >&2)
            book="$S3_QUEUE/$ARG_CODE_VERSION.web-hosting-queue.json"
            if [[ ! -s "$book" ]]; then
                echo "Book is empty"
                exit 1
            fi

            case $CONTENT_SOURCE in
                archive)
                    echo -n "$(cat $book | jq -er '.collection_id')" >$IO_BOOK/collection_id
                    echo -n "$(cat $book | jq -er '.server')" >$IO_BOOK/server
                ;;
                git)
                    echo -n "$(cat $book | jq -r '.slug')" >$IO_BOOK/slug
                    echo -n "$(cat $book | jq -r '.repo')" >$IO_BOOK/repo
                ;;
                *)
                    echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
                    exit 1
                ;;
            esac

            echo -n "$(cat $book | jq -r '.style')" >$IO_BOOK/style
            echo -n "$(cat $book | jq -r '.version')" >$IO_BOOK/version
            echo -n "$(cat $book | jq -r '.uuid')" >$IO_BOOK/uuid
        ;;
        archive-fetch)
            parse_book_dir

            # Validate inputs
            ensure_arg ARG_COLLECTION_ID
            ensure_arg ARG_COLLECTION_VERSION
            ensure_arg ARG_ARCHIVE_SERVER
            check_output_dir "${IO_ARCHIVE_FETCHED}"

            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/fetch-book.js#L38
            temp_dir=$(mktemp -d)
            yes | try neb get -r -d "${temp_dir}/does-not-exist-yet-dir" "$ARG_ARCHIVE_SERVER" "$ARG_COLLECTION_ID" "$ARG_COLLECTION_VERSION"

            try mv $temp_dir/does-not-exist-yet-dir/* $IO_ARCHIVE_FETCHED

        ;;
        archive-fetch-metadata)
            book_slugs_url='https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json'
            try wget "${book_slugs_url}" -O "${IO_ARCHIVE_FETCHED}/approved-book-list.json"
        ;;
        archive-assemble)
            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/assemble-book.js
            try neb assemble "${IO_ARCHIVE_FETCHED}" "${IO_ARCHIVE_BOOK}"
        ;;
        archive-assemble-metadata)
            target_dir=$IO_ARCHIVE_BOOK
            echo "{" > $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
            find $IO_ARCHIVE_FETCHED/ -path */m*/metadata.json | xargs cat | jq -r '. | "\"\(.id)\": \"\(.revised)\","' >> $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
            echo '"dummy": "dummy"' >> $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
            echo "}" >> $IO_ARCHIVE_BOOK/uuid-to-revised-map.json

            assemble-meta "$IO_ARCHIVE_BOOK/collection.assembled.xhtml" $IO_ARCHIVE_BOOK/uuid-to-revised-map.json "$target_dir/collection.assembled-metadata.json"
            rm $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
        ;;
        archive-link-extras)
            book_server=archive.cnx.org
            # https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/link-extras.js#L40
            try python3 /openstax/bakery-scripts/scripts/link_extras.py "${IO_ARCHIVE_BOOK}" "${book_server}" /openstax/bakery-scripts/scripts/canonical-book-list.json
        ;;
        archive-bake)
            parse_book_dir
            # Validate commandline arguments
            ensure_arg ARG_RECIPE_NAME

            try /openstax/recipes/bake_root -b "${ARG_RECIPE_NAME}" -r /openstax/cnx-recipes-recipes-output/ -i "${IO_ARCHIVE_BOOK}/collection.linked.xhtml" -o "${IO_ARCHIVE_BOOK}/collection.baked.xhtml"

            style_file="/openstax/cnx-recipes-styles-output/${ARG_RECIPE_NAME}-pdf.css"

            [[ -f "${style_file}" ]] || yell "Warning: Could not find style file for recipe name '${ARG_RECIPE_NAME}'"

            if [ -f "${style_file}" ]
            then
                cp "${style_file}" "${IO_ARCHIVE_BOOK}"
                try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename ${style_file})\" />&%" "${IO_ARCHIVE_BOOK}/collection.baked.xhtml"
            fi
        ;;
        archive-mathify)
            # Remove the mathified file if it already exists ecause the code assumes the file does not exist
            [[ -f "${IO_ARCHIVE_BOOK}/collection.mathified.xhtml" ]] && rm "${IO_ARCHIVE_BOOK}/collection.mathified.xhtml"

            try node /openstax/mathify/typeset/start.js -i "${IO_ARCHIVE_BOOK}/collection.baked.xhtml" -o "${IO_ARCHIVE_BOOK}/collection.mathified.xhtml" -f svg 
        ;;
        archive-pdf)
            parse_book_dir
            ensure_arg ARG_TARGET_PDF_FILENAME
            check_input_dir "${IO_ARCHIVE_BOOK}"
            check_output_dir "${IO_ARTIFACTS}"

            try prince -v --output="${IO_ARTIFACTS}/${ARG_TARGET_PDF_FILENAME}" "${IO_ARCHIVE_BOOK}/collection.mathified.xhtml"
        ;;
        archive-pdf-metadata)
            parse_book_dir
            ensure_arg CORGI_ARTIFACTS_S3_BUCKET
            ensure_arg ARG_TARGET_PDF_FILENAME
            check_output_dir "${IO_ARTIFACTS}"

            echo -n "https://$CORGI_ARTIFACTS_S3_BUCKET.s3.amazonaws.com/$ARG_TARGET_PDF_FILENAME" > $IO_ARTIFACTS/pdf_url
        ;;

        archive-bake-metadata)
            parse_book_dir
            ensure_arg ARG_COLLECTION_ID
            check_input_dir "${IO_ARCHIVE_FETCHED}"

            book_metadata="${IO_ARCHIVE_FETCHED}/metadata.json"
            book_uuid="$(cat $book_metadata | jq -r '.id')"
            book_version="$(cat $book_metadata | jq -r '.version')"
            book_legacy_id="$(cat $book_metadata | jq -r '.legacy_id')"
            book_legacy_version="$(cat $book_metadata | jq -r '.legacy_version')"
            book_ident_hash="$book_uuid@$book_version"
            book_license="$(cat $book_metadata | jq '.license')"
            target_dir="$IO_ARCHIVE_BOOK"
            book_slugs_file="/tmp/book-slugs.json"
            cat "$IO_ARCHIVE_FETCHED/approved-book-list.json" | jq ".approved_books|map(.books)|flatten" > "$book_slugs_file"
            cat "$IO_ARCHIVE_BOOK/collection.assembled-metadata.json" | \
                jq --arg ident_hash "$book_ident_hash" --arg uuid "$book_uuid" --arg version "$book_version" --argjson license "$book_license" \
                --arg legacy_id "$book_legacy_id" --arg legacy_version "$book_legacy_version" \
                '. + {($ident_hash): {id: $uuid, version: $version, license: $license, legacy_id: $legacy_id, legacy_version: $legacy_version}}' > "/tmp/collection.baked-input-metadata.json"
            try bake-meta /tmp/collection.baked-input-metadata.json "$target_dir/collection.baked.xhtml" "$book_uuid" "$book_slugs_file" "$target_dir/collection.baked-metadata.json"
        ;;
        archive-checksum)
            try checksum "$IO_ARCHIVE_BOOK" "$IO_ARCHIVE_BOOK"
        ;;
        archive-disassemble)
            try disassemble "$IO_ARCHIVE_BOOK/collection.baked.xhtml" "$IO_ARCHIVE_BOOK/collection.baked-metadata.json" "collection" "$IO_ARCHIVE_BOOK"
        ;;
        archive-patch-disassembled-links)
            target_dir="$IO_ARCHIVE_BOOK"
            try patch-same-book-links "$IO_ARCHIVE_BOOK" "$target_dir" "collection"
        ;;
        archive-jsonify)
            check_input_dir "${IO_ARCHIVE_BOOK}"
            check_output_dir "${IO_ARCHIVE_JSONIFIED}"
            check_output_dir "${IO_ARTIFACTS}"

            target_dir="$IO_ARCHIVE_JSONIFIED"
            
            try mkdir -p $target_dir
            try jsonify "$IO_ARCHIVE_BOOK" "$target_dir"
            try cp "$target_dir/collection.toc.json" "$IO_ARTIFACTS/"
            try jsonschema -i "$target_dir/collection.toc.json" /openstax/bakery-scripts/scripts/book-schema.json
            for jsonfile in "$target_dir/"*@*.json; do
                #ignore -metadata.json files
                if [[ $jsonfile != *-metadata.json ]]; then
                    try jsonschema -i "$jsonfile" /openstax/bakery-scripts/scripts/page-schema.json
                fi
            done
        ;;
        archive-validate-xhtml)
            for xhtmlfile in $(find $IO_ARCHIVE_JSONIFIED -name '*@*.xhtml')
            do
                try java -cp /openstax/xhtml-validator/xhtml-validator.jar org.openstax.xml.Main "$xhtmlfile" duplicate-id broken-link
            done
        ;;
        archive-upload-book)
            parse_book_dir
            ensure_arg ARG_S3_BUCKET_NAME
            ensure_arg ARG_CODE_VERSION
            ensure_arg AWS_ACCESS_KEY_ID
            ensure_arg AWS_SECRET_ACCESS_KEY

            check_input_dir "${IO_ARCHIVE_BOOK}"
            check_input_dir "${IO_ARCHIVE_FETCHED}"
            check_input_dir "${IO_ARCHIVE_JSONIFIED}"
            check_output_dir "${IO_ARCHIVE_UPLOAD}"

            s3_bucket_prefix="apps/archive/${ARG_CODE_VERSION}"

            book_metadata="${IO_ARCHIVE_FETCHED}/metadata.json"
            resources_dir="${IO_ARCHIVE_BOOK}/resources"
            target_dir="${IO_ARCHIVE_UPLOAD}/contents"
            mkdir -p "$target_dir"
            book_uuid="$(cat $book_metadata | jq -r '.id')"
            book_version="$(cat $book_metadata | jq -r '.version')"

            for jsonfile in "$IO_ARCHIVE_JSONIFIED/"*@*.json; do try cp "$jsonfile" "$target_dir/$(basename $jsonfile)"; done;
            for xhtmlfile in "$IO_ARCHIVE_JSONIFIED/"*@*.xhtml; do try cp "$xhtmlfile" "$target_dir/$(basename $xhtmlfile)"; done;
            try aws s3 cp --recursive "$target_dir" "s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents"
            try copy-resources-s3 "$resources_dir" "${ARG_S3_BUCKET_NAME}" "${s3_bucket_prefix}/resources"

            #######################################
            # UPLOAD BOOK LEVEL FILES LAST
            # so that if an error is encountered
            # on prior upload steps, those files
            # will not be found by watchers
            #######################################
            toc_s3_link_json="s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.json"
            toc_s3_link_xhtml="s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.xhtml"
            try aws s3 cp "$IO_ARCHIVE_JSONIFIED/collection.toc.json" "$toc_s3_link_json"
            try aws s3 cp "$IO_ARCHIVE_JSONIFIED/collection.toc.xhtml" "$toc_s3_link_xhtml"

            echo "DONE: See book at https://${ARG_S3_BUCKET_NAME}.s3.amazonaws.com/${s3_bucket_prefix}/contents/$book_uuid@$book_version.xhtml (maybe rename '-gatekeeper' to '-primary')"
        ;;

        archive-report-book-complete)
            ensure_arg ARG_CODE_VERSION
            ensure_arg WEB_QUEUE_STATE_S3_BUCKET

            ensure_arg AWS_ACCESS_KEY_ID
            ensure_arg AWS_SECRET_ACCESS_KEY
            check_input_dir $IO_BOOK

            CONTENT_SOURCE=archive
            bucketPrefix=archive-dist
            codeVersion=$ARG_CODE_VERSION
            queueStateBucket=$WEB_QUEUE_STATE_S3_BUCKET

            case $CONTENT_SOURCE in
            archive)
                book_id="$(cat $IO_BOOK/collection_id)"
                ;;
            git)
                book_id="$(cat $IO_BOOK/slug)"
                ;;
            *)
                echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
                exit 1
                ;;
            esac
                        
            version="$(cat $IO_BOOK/version)"
            complete_filename=".${bucketPrefix}.$book_id@$version.complete"
            try date -Iseconds > "/tmp/$complete_filename"

            try aws s3 cp "/tmp/$complete_filename" "s3://${queueStateBucket}/${codeVersion}/$complete_filename"
        ;;

        git-fetch)
            parse_book_dir
            check_output_dir "${IO_FETCHED}"

            ensure_arg ARG_REPO_NAME
            ensure_arg ARG_GIT_REF
            ensure_arg ARG_TARGET_SLUG_NAME

            [[ "${ARG_GIT_REF}" == latest ]] && ARG_GIT_REF=main
            [[ "${ARG_REPO_NAME}" == */* ]] || ARG_REPO_NAME="openstax/${ARG_REPO_NAME}"

            remote_url="https://github.com/${ARG_REPO_NAME}.git"
            
            if [[ ${GH_SECRET_CREDS} ]]; then
                creds_dir=tmp-gh-creds
                creds_file="$creds_dir/gh-creds"
                git config --global credential.helper "store --file=$creds_file"
                mkdir "$creds_dir"
                # Do not show creds
                echo "https://$GH_SECRET_CREDS@github.com" > "$creds_file" 2>&1
            fi

            # If ARG_GIT_REF starts with '@' then it is a commit and check out the individual commit
            # Or, https://stackoverflow.com/a/7662531
            [[ ${ARG_GIT_REF} =~ ^[a-f0-9]{40}$ ]] && ARG_GIT_REF="@${ARG_GIT_REF}"

            if [[ ${ARG_GIT_REF} = @* ]]; then
                git_commit="${ARG_GIT_REF:1}"
                GIT_TERMINAL_PROMPT=0 try git clone --depth 50 "${remote_url}" "${IO_FETCHED}"
                pushd "${IO_FETCHED}"
                try git reset --hard "${git_commit}"
                # If the commit was not recent, try cloning the whole repo
                if [[ $? != 0 ]]; then
                    popd
                    GIT_TERMINAL_PROMPT=0 try git clone "${remote_url}" "${IO_FETCHED}"
                    pushd "${IO_FETCHED}"
                    try git reset --hard "${git_commit}"
                fi
                popd
            else
                GIT_TERMINAL_PROMPT=0 try git clone --depth 1 "${remote_url}" --branch "${ARG_GIT_REF}" "${IO_FETCHED}"
            fi

            if [[ ! -f "${IO_FETCHED}/collections/${ARG_TARGET_SLUG_NAME}.collection.xml" ]]; then
                echo "No matching book for slug in this repo"
                exit 1
            fi
        ;;

        git-fetch-metadata)
            check_input_dir "${IO_FETCHED}"
            check_output_dir "${IO_FETCHED}"
            check_output_dir "${IO_RESOURCES}"
            check_output_dir "${IO_UNUSED_RESOURCES}"

            
            try fetch-update-meta "${IO_FETCHED}/.git" "${IO_FETCHED}/modules" "${IO_FETCHED}/collections" "${ARG_GIT_REF}" "${IO_FETCHED}/canonical.json"
            try rm -rf "${IO_FETCHED}/.git"
            try rm -rf "$creds_dir"

            try fetch-map-resources "${IO_FETCHED}/modules" "${IO_FETCHED}/media" . "${IO_UNUSED_RESOURCES}"
            # Either the media is in resources or unused-resources, this folder should be empty (-d will fail otherwise)
            try rm -d "${IO_FETCHED}/media"
        ;;

        git-assemble)
            check_input_dir "${IO_FETCHED}"
            check_output_dir "${IO_ASSEMBLED}"
            
            shopt -s globstar nullglob
            for collection in "${IO_FETCHED}/collections/"*; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                    if [[ "$slug_name" != "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                        continue
                    fi
                fi
                try cp "$collection" "${IO_FETCHED}/modules/collection.xml"

                try neb assemble "${IO_FETCHED}/modules" temp-assembly/

                try cp "temp-assembly/collection.assembled.xhtml" "${IO_ASSEMBLED}/$slug_name.assembled.xhtml"
                try rm -rf temp-assembly
                try rm "${IO_FETCHED}/modules/collection.xml"
            done
            shopt -u globstar nullglob
        ;;

        git-assemble-meta)
            check_input_dir "${IO_FETCHED}"
            check_input_dir "${IO_ASSEMBLED}"
            check_output_dir "${IO_ASSEMBLE_META}"

            shopt -s globstar nullglob
            # Create an empty map file for invoking assemble-meta
            echo "{}" > uuid-to-revised-map.json
            for collection in "${IO_ASSEMBLED}/"*.assembled.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                    if [[ "$slug_name" != "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                        continue
                    fi
                fi
                try assemble-meta "${IO_ASSEMBLED}/$slug_name.assembled.xhtml" uuid-to-revised-map.json "${IO_ASSEMBLE_META}/${slug_name}.assembled-metadata.json"
            done
            try rm uuid-to-revised-map.json
            shopt -u globstar nullglob
        ;;

        git-bake)
            parse_book_dir
            ensure_arg ARG_RECIPE_NAME
            check_input_dir "${IO_ASSEMBLED}"
            check_output_dir "${IO_BAKED}"

            # FIXME: We assume that every book in the group uses the same style
            # This assumption will not hold true forever, and book style + recipe name should
            # be pulled from fetched-book-group (while still allowing injection w/ CLI)

            # FIXME: Style devs will probably not like having to bake multiple books repeatedly,
            # especially since they shouldn't care about link-extras correctness during their
            # work cycle.

            # FIXME: Separate style injection step from baking step. This is way too much work to change a line injected into the head tag
            style_file="/openstax/cnx-recipes-styles-output/${ARG_RECIPE_NAME}-pdf.css"

            if [[ -f "$style_file" ]]
                then
                    try cp "$style_file" "${IO_BAKED}/the-style-pdf.css"
                else
                    echo "Warning: Style Not Found" > "${IO_BAKED}/stderr"
            fi

            shopt -s globstar nullglob
            for collection in "${IO_ASSEMBLED}/"*.assembled.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                    if [[ "$slug_name" != "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                        continue
                    fi
                fi
                try /openstax/recipes/bake_root -b "${ARG_RECIPE_NAME}" -r /openstax/cnx-recipes-recipes-output/ -i "${IO_ASSEMBLED}/$slug_name.assembled.xhtml" -o "${IO_BAKED}/$slug_name.baked.xhtml"
                if [[ -f "$style_file" ]]
                    then
                        try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"the-style-pdf.css\" />&%" "${IO_BAKED}/$slug_name.baked.xhtml"
                fi
            done
            shopt -u globstar nullglob
        ;;

        git-bake-meta)
            check_input_dir "${IO_ASSEMBLE_META}"
            check_input_dir "${IO_BAKED}"
            check_output_dir "${IO_BAKE_META}"

            shopt -s globstar nullglob
            for collection in "${IO_BAKED}/"*.baked.xhtml; do
                slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
                if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                    if [[ "$slug_name" != "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                        continue
                    fi
                fi

                try bake-meta "${IO_ASSEMBLE_META}/$slug_name.assembled-metadata.json" "${IO_BAKED}/$slug_name.baked.xhtml" "" "" "${IO_BAKE_META}/$slug_name.baked-metadata.json"
            done
            shopt -u globstar nullglob
        ;;

        git-link)
            parse_book_dir
            ensure_arg ARG_TARGET_SLUG_NAME
            check_input_dir "${IO_BAKED}"
            check_input_dir "${IO_BAKE_META}"
            check_output_dir "${IO_LINKED}"

            if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
                try link-single "${IO_BAKED}" "${IO_BAKE_META}" "${ARG_TARGET_SLUG_NAME}" "${IO_LINKED}/${ARG_TARGET_SLUG_NAME}.linked.xhtml" --mock-otherbook
            else
                try link-single "${IO_BAKED}" "${IO_BAKE_META}" "${ARG_TARGET_SLUG_NAME}" "${IO_LINKED}/${ARG_TARGET_SLUG_NAME}.linked.xhtml"
            fi
        ;;

        git-disassemble)
            parse_book_dir
            ensure_arg ARG_TARGET_SLUG_NAME
            check_input_dir "${IO_LINKED}"
            check_input_dir "${IO_BAKE_META}"
            check_output_dir "${IO_DISASSEMBLED}"

            try disassemble "${IO_LINKED}/$ARG_TARGET_SLUG_NAME.linked.xhtml" "${IO_BAKE_META}/$ARG_TARGET_SLUG_NAME.baked-metadata.json" "$ARG_TARGET_SLUG_NAME" "${IO_DISASSEMBLED}"
        ;;

        git-patch-disassembled-links)
            parse_book_dir
            ensure_arg ARG_TARGET_SLUG_NAME
            check_input_dir "${IO_DISASSEMBLED}"
            check_output_dir "${IO_DISASSEMBLE_LINKED}"

            try patch-same-book-links "${IO_DISASSEMBLED}" "${IO_DISASSEMBLE_LINKED}" "$ARG_TARGET_SLUG_NAME"
            try cp "${IO_DISASSEMBLED}"/*@*-metadata.json "${IO_DISASSEMBLE_LINKED}"
            try cp "${IO_DISASSEMBLED}"/"$ARG_TARGET_SLUG_NAME".toc* "${IO_DISASSEMBLE_LINKED}"
        ;;

        git-jsonify)
            parse_book_dir
            ensure_arg ARG_TARGET_SLUG_NAME
            check_input_dir "${IO_DISASSEMBLE_LINKED}"
            check_output_dir "${IO_JSONIFIED}"

            try jsonify "${IO_DISASSEMBLE_LINKED}" "${IO_JSONIFIED}"
            try jsonschema -i "${IO_JSONIFIED}/${ARG_TARGET_SLUG_NAME}.toc.json" /openstax/bakery-scripts/scripts/book-schema-git.json

            for jsonfile in "${IO_JSONIFIED}/"*@*.json; do
                try jsonschema -i "$jsonfile" /openstax/bakery-scripts/scripts/page-schema.json
            done
        ;;

        git-validate-xhtml)
            check_input_dir "${IO_DISASSEMBLE_LINKED}"

            for xhtmlfile in $(find ${IO_DISASSEMBLE_LINKED} -name '*.xhtml')
            do
                say "XHTML-validating ${xhtmlfile}"
                try java -cp /openstax/xhtml-validator/xhtml-validator.jar org.openstax.xml.Main "$xhtmlfile" duplicate-id broken-link
            done
        ;;
        git-mathify)
            parse_book_dir
            ensure_arg ARG_TARGET_SLUG_NAME

            check_input_dir "${IO_LINKED}"
            check_input_dir "${IO_BAKED}"
            check_output_dir "${IO_MATHIFIED}"

            # Style needed because mathjax will size converted math according to surrounding text
            try cp "${IO_BAKED}/the-style-pdf.css" "${IO_LINKED}"
            try cp "${IO_BAKED}/the-style-pdf.css" "${IO_MATHIFIED}"
            try node /openstax/mathify/typeset/start.js -i "${IO_LINKED}/$ARG_TARGET_SLUG_NAME.linked.xhtml" -o "${IO_MATHIFIED}/$ARG_TARGET_SLUG_NAME.mathified.xhtml" -f svg
        ;;
        git-pdfify)
            parse_book_dir
            ensure_arg ARG_TARGET_SLUG_NAME
            ensure_arg ARG_TARGET_PDF_FILENAME

            check_input_dir "${IO_MATHIFIED}"
            check_output_dir "${IO_ARTIFACTS}"

            try prince -v --output="${IO_ARTIFACTS}/${ARG_TARGET_PDF_FILENAME}" "${IO_MATHIFIED}/${ARG_TARGET_SLUG_NAME}.mathified.xhtml"
        ;;
        git-pdfify-meta)
            check_output_dir "${IO_ARTIFACTS}"

            ensure_arg ARG_S3_BUCKET_NAME
            ensure_arg ARG_TARGET_PDF_FILENAME

            pdf_url="https://${ARG_S3_BUCKET_NAME}.s3.amazonaws.com/${ARG_TARGET_PDF_FILENAME}"
            try echo -n "${pdf_url}" > "${IO_ARTIFACTS}/pdf_url"

            echo "DONE: See book at ${pdf_url}"
        ;;
        git-upload-book)
            parse_book_dir
            check_input_dir "${IO_JSONIFIED}"
            check_input_dir "${IO_RESOURCES}"
            check_output_dir "${IO_ARTIFACTS}"

            ensure_arg ARG_S3_BUCKET_NAME
            ensure_arg ARG_CODE_VERSION
            ensure_arg ARG_TARGET_SLUG_NAME
            ensure_arg AWS_ACCESS_KEY_ID
            ensure_arg AWS_SECRET_ACCESS_KEY

            s3_bucket_prefix="apps/archive/${ARG_CODE_VERSION}"

            # Parse the UUID and versions from the book metadata since it will be accessible
            # for any pipeline (web-hosting or web-preview) and to be self-consistent
            # metadata and values used.
            book_metadata="${IO_JSONIFIED}/$ARG_TARGET_SLUG_NAME.toc.json"
            book_uuid=$(jq -r '.id' "$book_metadata")
            book_version=$(jq -r '.version' "$book_metadata")
            for jsonfile in "$IO_JSONIFIED/"*@*.json; do cp "$jsonfile" "$IO_ARTIFACTS/$(basename "$jsonfile")"; done;
            for xhtmlfile in "$IO_JSONIFIED/"*@*.xhtml; do cp "$xhtmlfile" "$IO_ARTIFACTS/$(basename "$xhtmlfile")"; done;
            try aws s3 cp --recursive "$IO_ARTIFACTS" "s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents"
            try copy-resources-s3 "${IO_RESOURCES}" "${ARG_S3_BUCKET_NAME}" "${s3_bucket_prefix}/resources"

            #######################################
            # UPLOAD BOOK LEVEL FILES LAST
            # so that if an error is encountered
            # on prior upload steps, those files
            # will not be found by watchers
            #######################################
            toc_s3_link_json="s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.json"
            toc_s3_link_xhtml="s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.xhtml"
            try aws s3 cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.json" "$toc_s3_link_json"
            try aws s3 cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.xhtml" "$toc_s3_link_xhtml"

            try cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.json" "$IO_ARTIFACTS/"
            try cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.xhtml" "$IO_ARTIFACTS/"

            echo "DONE: See book at https://${ARG_S3_BUCKET_NAME}.s3.amazonaws.com/${s3_bucket_prefix}/contents/$book_uuid@$book_version.xhtml (maybe rename '-gatekeeper' to '-primary')"
        ;;

        --help)
            die "This script uses environment variables extensively to change where to read/write content from. See the top of this file for a complete list"
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
    unset_book_vars
    say "==> Finished: $*"
}


case $1 in
    all-archive-pdf)
        do_step_named local-create-book-directory "${@:2}"
        do_step_named archive-look-up-book
        do_step_named archive-fetch
        do_step_named archive-fetch-metadata
        do_step_named archive-assemble
        do_step_named archive-link-extras
        do_step_named archive-bake
        do_step_named archive-mathify
        do_step_named archive-pdf
    ;;
    all-archive-web)
        do_step_named local-create-book-directory "${@:2}"
        do_step_named archive-look-up-book
        do_step_named archive-fetch
        do_step_named archive-fetch-metadata
        do_step_named archive-assemble
        do_step_named archive-assemble-metadata
        do_step_named archive-link-extras
        do_step_named archive-bake
        do_step_named archive-bake-metadata
        do_step_named archive-checksum
        do_step_named archive-disassemble
        do_step_named archive-patch-disassembled-links
        do_step_named archive-jsonify
        do_step_named archive-validate-xhtml
        # do_step_named archive-upload-book
    ;;
    all-git-web)
        do_step_named local-create-book-directory "${@:2}"
        do_step_named git-look-up-book
        do_step_named git-fetch
        do_step_named git-fetch-metadata
        do_step_named git-assemble
        do_step_named git-assemble-meta
        do_step_named git-bake
        do_step_named git-bake-meta
        do_step_named git-link
        do_step_named git-disassemble
        do_step_named git-patch-disassembled-links
        do_step_named git-jsonify
        # do_step_named git-validate-xhtml
    ;;
    all-git-pdf)
        do_step_named local-create-book-directory "${@:2}"
        do_step_named git-look-up-book
        do_step_named git-fetch
        do_step_named git-fetch-metadata
        do_step_named git-assemble
        do_step_named git-assemble-meta
        do_step_named git-bake
        do_step_named git-bake-meta
        do_step_named git-link
        
        do_step_named git-mathify
        do_step_named git-pdfify
    ;;
    *) # Assume the user is only running one step
        do_step $@
    ;;
esac
