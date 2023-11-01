#!/usr/bin/env bash

# This is run every time the docker container starts up.

# set -e
set -Eeuo pipefail

# Trace and log if TRACE_ON is set
TRACE_ON=${TRACE_ON:-}
[[ $TRACE_ON ]] && set -x && export PS4='+ [${BASH_SOURCE##*/}:${LINENO}] '

# https://stackoverflow.com/questions/5947742/how-to-change-the-output-color-of-echo-in-linux
c_red=''
c_green=''
c_yellow=''
c_blue=''
c_purple=''
c_cyan=''
c_none=''
if [[ $(tput colors) -ge 8 ]]; then
    # LCOV_EXCL_START
    c_red=$(tput setaf 1)
    c_green=$(tput setaf 2)
    c_yellow=$(tput setaf 3)
    c_blue=$(tput setaf 4)
    c_purple=$(tput setaf 5)
    c_cyan=$(tput setaf 6)
    c_none=$(tput sgr0) # Keep this last so TRACE=true does not cause everything to be cyan
    # LCOV_EXCL_STOP
fi

# https://stackoverflow.com/a/25515370
say() { echo -e "${c_green}$*${c_none}"; }
warn() { echo -e "${c_yellow}$*${c_none}"; }
yell() { >&2 echo -e "$0: $c_red$*$c_none"; }
die() {
    # LCOV_EXCL_START
    yell "$1"
    exit 112
    # LCOV_EXCL_STOP
}

[[ $PROJECT_ROOT ]] || die "Environment variable PROJECT_ROOT was not set. It should be set inside the Dockerfile"

STEP_CONFIG_FILE=${STEP_CONFIG_FILE:-$PROJECT_ROOT/step-config.json}
DOCKERFILES_ROOT=${DOCKERFILES_ROOT:-/dockerfiles}
BAKERY_SCRIPTS_ROOT=${BAKERY_SCRIPTS_ROOT:-$PROJECT_ROOT/bakery-src}
PYTHON_VENV_ROOT=${PYTHON_VENV_ROOT:-$PROJECT_ROOT/venv}
COOKBOOK_ROOT=${COOKBOOK_ROOT:-$PROJECT_ROOT/cookbook}
MATHIFY_ROOT=${MATHIFY_ROOT:-$PROJECT_ROOT/mathify}
JS_UTILS_STUFF_ROOT=${JS_UTILS_STUFF_ROOT:-$PROJECT_ROOT/bakery-js}
BOOK_STYLES_ROOT=${BOOK_STYLES_ROOT:-$PROJECT_ROOT/ce-styles/styles/output}
XHTML_VALIDATOR_ROOT=${XHTML_VALIDATOR_ROOT:-$PROJECT_ROOT/xhtml-validator/build/libs}
START_AT_STEP=${START_AT_STEP:-}
STOP_AT_STEP=${STOP_AT_STEP:-}
KCOV_DIR=${KCOV_DIR:-}
LOCAL_ATTIC_DIR=${LOCAL_ATTIC_DIR:-}
JAVA_DEBUG=${JAVA_DEBUG:-}
JS_DEBUG=${JS_DEBUG:-}
NODE_OPTIONS=${NODE_OPTIONS:-}
STUB_UPLOAD=${STUB_UPLOAD:-}

if [[ $JS_DEBUG ]]; then
    export NODE_DEBUG_PORT=9229 # LCOV_EXCL_LINE
    export NODE_OPTIONS="--inspect-brk=0.0.0.0:$NODE_DEBUG_PORT" # LCOV_EXCL_LINE
fi

if [[ $STUB_UPLOAD ]]; then
    say "STUBBING UPLOAD FUNCTIONS"
    export AWS_ACCESS_KEY_ID="test"
    export AWS_SECRET_ACCESS_KEY="test"
    if [[ $STUB_UPLOAD == "corgi" ]]; then
        export CORGI_CLOUDFRONT_URL="https://test-cloudfront-url"
        export REX_PROD_PREVIEW_URL="https://rex-test"
    fi
    export CODE_VERSION="test"

    function get_stub_output_dir() {
        output_dirs=$(jq -r ".steps.\"$step_name\".outputDirs|@sh" < $STEP_CONFIG_FILE)
        to_return=''
        for output_dir in $output_dirs; do
            # Prefer IO_ARTIFACTS, fallback to using first output directory in the list
            if [[ $to_return == '' || $output_dir == "'IO_ARTIFACTS'" ]]; then
                to_return="$output_dir"
            fi
        done
        expect_value "$to_return" "get_stub_output_dir: Expected to find output directory."
        echo "$to_return" | tr -d "'"
    }

    function aws() {
        pointer=$(get_stub_output_dir)
        aws_calls=$(find "${!pointer}" -name 'aws_args_*' | wc -l)
        echo "$@" > "${!pointer}/aws_args_$((aws_calls+1))"
    }

    function copy-resources-s3() {
        pointer=$(get_stub_output_dir)
        copy_resouce_s3_calls=$(find "${!pointer}" -name 'copy_resources_s3_args_*' | wc -l)
        echo "$@" > "${!pointer}/copy_resources_s3_args_$((copy_resouce_s3_calls+1))"
    }
fi

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
    [[ $1 ]] || die "This function takes exactly one argument and it is missing"
    pointer=$1 # https://stackoverflow.com/a/55331060
    dir_name="${!pointer}"
    [[ $dir_name ]] || die "This input directory environment variable is not set ($1='$dir_name')"
    [[ -d $dir_name ]] || die "Expected directory to exist but it did not ($1='$dir_name'). Maybe an earlier step needs to run."
}
function check_output_dir() {
    [[ $1 ]] || die "This function takes exactly one argument and it is missing"
    pointer=$1 # https://stackoverflow.com/a/55331060
    dir_name="${!pointer}"
    [[ $dir_name ]] || die "This output directory environment variable is not set ($1='$dir_name')"
    # Auto-create directories only in local dev mode. In Concourse Pip}elines these directories should already exist.
    if [[ $LOCAL_ATTIC_DIR != '' && ! -d $dir_name ]]; then
        mkdir -p $dir_name
    fi
    [[ -d $dir_name ]] || die "Expected output directory to exist but it was missing ($1='$dir_name'). it needs to be added to the concourse job"
}

function do_xhtml_validate() {
    failure=false
    dir_name=$1
    file_pattern=$2
    check=$3
    extra_vars=""
    echo "Validating xhtml links in $dir_name"
    if [[ $JAVA_DEBUG == 1 ]]
    then
        extra_vars="-agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=${DEBUG_HOST}:${JAVA_DEBUG_PORT}" # LCOV_EXCL_LINE 
    fi

    java $extra_vars -cp $XHTML_VALIDATOR_ROOT/xhtml-validator.jar org.openstax.xml.Main  "$dir_name" $file_pattern $check broken-link || failure=true
    if $failure; then
        exit 1 # LCOV_EXCL_LINE
    fi
}

# FIXME: We assume that every book in the group uses the same style
# This assumption will not hold true forever, and book style + recipe name should
# be pulled from fetched-book-group (while still allowing injection w/ CLI)


# FIXME: Style devs will probably not like having to bake multiple books repeatedly,
# especially since they shouldn't care about link-extras correctness during their
# work cycle.

function read_style() {
    slug_name=$1
    style_name=$(xmlstarlet sel -t --match "//*[@style][@slug=\"$slug_name\"]" --value-of '@style' < $IO_FETCHED/META-INF/books.xml)
    echo $style_name
}

function read_book_slugs() {
    if [[ -f "$IO_BOOK/slugs" ]]; then
        # Exclude blanks lines
        awk '$0 { print }' "$IO_BOOK/slugs"
    else
        fetched="$IO_FETCHED"
        if [[ ! -d "$fetched" ]]; then
            fetched="$IO_FETCH_META"
        fi
        if [[ ! -d "$fetched" ]]; then
            die "read_book_slugs: Could not find books.xml. Make sure you included IO_FETCHED or IO_FETCH_META as an input to this step."  # LCOV_EXCL_LINE
        fi
        xmlstarlet sel -t --match "//*[@slug]" --value-of '@slug' --nl < "$fetched/META-INF/books.xml"
    fi
}

function expect_value() {
  if [[ -z "$1" ]]; then
    die "${2:-"Missing required argument"}"  # LCOV_EXCL_LINE
  fi
}

function get_s3_name() {
    filename="$(basename "$1")"
    repo="$(cat "$IO_BOOK/repo")"
    version="$(cat "$IO_BOOK/version")"
    job_id="$(cat "$IO_BOOK/job_id")"
    for varname in repo version job_id filename; do
        expect_value "${!varname-}" "get_s3_name: Expected value for \"$varname\""
    done
    s3_name="${repo%%/}-$version-$job_id-$filename"
    s3_name_no_slashes="$(echo "$s3_name" | sed 's/\//-/g')"
    # AWS CLI url encodes urls, no need to do it manually here
    echo "$s3_name_no_slashes"
}

function upload_book_artifacts() {
    content_type="${1:-}"
    output_path="${2:-}"
    for varname in ARG_S3_BUCKET_NAME output_path content_type; do
        expect_value "${!varname-}" "upload_book_artifacts: Expected value for \"$varname\""
    done
    book_slug_urls=()
    while IFS='|' read -r file_to_upload slug; do
        for varname in file_to_upload slug; do
            expect_value "${!varname-}" "upload_book_artifacts: Expected value for \"$varname\""
        done

        s3_name="$(set -Eeuo pipefail && get_s3_name "$file_to_upload")"
        s3_name_url_encd="$(printf %s "$s3_name" | jq -sRr @uri)"

        url="https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$s3_name_url_encd"
        book_slug_urls+=("$(jo url="$url" slug="$slug")")

        aws s3 cp "$file_to_upload" "s3://$ARG_S3_BUCKET_NAME/$s3_name" \
            --acl "public-read" \
            --content-type "$content_type"
    done
    if [[ ${#book_slug_urls[@]} == 0 ]]; then
        die "Did not get any book artifacts to upload."  # LCOV_EXCL_LINE
    fi
    jo -a "${book_slug_urls[@]}" > "$output_path/artifact_urls.json"
}

function parse_book_dir() {
    check_input_dir IO_BOOK

    [[ -f $IO_BOOK/repo ]] && ARG_REPO_NAME="$(cat $IO_BOOK/repo)"
    ARG_GIT_REF="$(cat $IO_BOOK/version)"
}

# Concourse-CI runs each step in a separate process so parse_book_dir() needs to
# reset between each step
function unset_book_vars() {
    unset ARG_REPO_NAME
    unset ARG_GIT_REF
}

function do_step() {
    step_name=$1

    # Parse the commandline args (runs in concourse and locally though only some args are used locally)
    shift 1

    while [ -n "${1:-}" ]; do
        case "$1" in
            --ref) shift; arg_ref=$1 ;;
            --repo) shift; arg_repo=$1 ;;
            --book-slug) shift; arg_book_slug=$1 ;;
            *) # LCOV_EXCL_START
                echo -e "Invalid argument '$1'"
                exit 2
                # LCOV_EXCL_END
            ;;
        esac
        shift
    done


    case $step_name in
        shell | '/bin/bash' | '/bin/sh')
            bash # LCOV_EXCL_LINE
            return # LCOV_EXCL_LINE
        ;;
        local-create-book-directory)
            # This step is normally done by the concourse resource but for local development it is done here

            repo="$arg_repo"
            version="$arg_ref"

            ensure_arg repo 'Specify repo name'
            ensure_arg version 'Specify repo/branch/tag/commit or archive collection version (e.g. latest)'

            [[ -d $INPUT_SOURCE_DIR ]] || mkdir "$INPUT_SOURCE_DIR"

            check_output_dir INPUT_SOURCE_DIR

            # Write out the files
            echo "$repo" > "$INPUT_SOURCE_DIR/repo"
            if [[ -n "${arg_book_slug-}" ]]; then
                # CORGI does not include a new line after the slug. Simulate that with echo -n
                echo -n "$arg_book_slug" > "$INPUT_SOURCE_DIR/slugs" 
            fi
            echo "$version" > "$INPUT_SOURCE_DIR/version"
            # Dummy files
            echo '-123456' > "$INPUT_SOURCE_DIR/id" # job_id
            echo '{"content_server":{"name":"not_a_real_job_json_file"}}' > "$INPUT_SOURCE_DIR/job.json"

            return
        ;;
        look-up-book)
            ensure_arg INPUT_SOURCE_DIR

            check_input_dir INPUT_SOURCE_DIR
            check_output_dir IO_BOOK
            
            tail "$INPUT_SOURCE_DIR"/*
            cp "$INPUT_SOURCE_DIR/id" "$IO_BOOK/job_id"
            cp "$INPUT_SOURCE_DIR/version" "$IO_BOOK/version"
            cp "$INPUT_SOURCE_DIR/repo" "$IO_BOOK/repo"
            # CORGI should always provide slugs, but that is not true on local
            if [[ -f "$INPUT_SOURCE_DIR/slugs" ]]; then
                cp "$INPUT_SOURCE_DIR/slugs" "$IO_BOOK/slugs"
            fi

            return
        ;;
    esac

    # Check that the input dirs, output dirs, and environment variables are set before running the step:

    step_entry=$(jq  -r ".steps.\"$step_name\"|not|not" < $STEP_CONFIG_FILE)

    if [[ "$step_entry" == 'false' ]]; then
        die "ERROR: Could not find step or pipeline named '$step_name'. Type --help to see a list of valid steps" # LCOV_EXCL_LINE
    else
        input_dirs=$(jq  -r ".steps.\"$step_name\".inputDirs|@sh"  < $STEP_CONFIG_FILE)
        output_dirs=$(jq -r ".steps.\"$step_name\".outputDirs|@sh" < $STEP_CONFIG_FILE)
        required_envs=$(jq -r ".steps.\"$step_name\".requiredEnv|@sh" < $STEP_CONFIG_FILE)

        for required_env in $required_envs; do # LCOV_EXCL_LINE
            ensure_arg $(echo $required_env | tr -d "'") # LCOV_EXCL_LINE
        done
        for input_dir in $input_dirs; do
            check_input_dir $(echo $input_dir | tr -d "'")
        done
        for output_dir in $output_dirs; do
            check_output_dir $(echo $output_dir | tr -d "'")
        done
    fi

    step_file="$DOCKERFILES_ROOT/steps/$step_name.bash"

    if [[ -f $step_file ]]; then
        source $step_file
    else
        die "Invalid command. The first argument needs to be a command like 'fetch'. Instead, it was '$step_name'" # LCOV_EXCL_LINE
    fi
}

function do_step_named() {
    step_name=$1
    if [[ $START_AT_STEP == $step_name ]]; then
        START_AT_STEP=''
    elif [[ $START_AT_STEP ]]; then
        say "==> Skipping $*"
    fi
    if [[ $STOP_AT_STEP == $step_name ]]; then
        say "==> Done because STOP_AT_STEP='$STOP_AT_STEP'"
        # Ensure no other steps run by setting START_AT_STEP to something invalid
        START_AT_STEP='__nonexistent_step__'
        exit 0
    fi

    # FIXME: Cannot select a book slug during local development when --start-at
    #        is used. The slugs file is written during local-create-book-directory
    #        and look-up-book. These steps are skipped when START_AT_STEP is defined.
    # POSSIBLE FIX: Stop skipping these two steps
    # PROBLEM: many steps, like step-fetch, assume these steps will be skipped
    #          and that the values in IO_BOOK will not change once written
    if [[ ! $START_AT_STEP ]]; then
        [[ $LOCAL_ATTIC_DIR ]] && simulate_dirs_before $step_name
        say "==> Starting: $*"
        do_step $@
        [[ $LOCAL_ATTIC_DIR ]] && simulate_dirs_after $step_name && unset_book_vars
        say "==> Finished: $*"
    fi
}

function simulate_dirs_before() {
    step_name=$1
    say "==> Preparing: $step_name"
    original_current_dir=$(pwd)

    input_dirs=$(jq  -r ".steps.\"$step_name\".inputDirs|@sh"  < $STEP_CONFIG_FILE)
    [[ $step_name == 'look-up-book' ]] && input_dirs='INPUT_SOURCE_DIR'

    # Delete all non-attic directories
    while IFS= read -r -d '' child_dir_path; do # generic for loop
        child_dir_name=$(basename $child_dir_path)
        if [[ $child_dir_name != $LOCAL_ATTIC_DIR ]]; then
            warn "Previous step left an extra directory. Try to be more tidy '$child_dir_path'"
        fi
    done <   <(find . -maxdepth 1 -mindepth 1 -type d -print0) # LCOV_EXCL_LINE

    # Copy directories from the attic into the workspace
    if [[ $input_dirs != null ]]; then
        for io_name in $input_dirs; do
            io_name=$(echo $io_name | tr -d "'")  # unquote from jq
            pointer=$io_name # https://stackoverflow.com/a/55331060
            child_dir_path="${!pointer}"

            if [[ -d "$LOCAL_ATTIC_DIR/$io_name" ]]; then
                if [[ -d $child_dir_path ]]; then
                    warn "BUG: We should not have directories checked out from the attic at this point. Maybe turn this into a warning in the future" # LCOV_EXCL_LINE
                    rm -rf "$child_dir_path" # LCOV_EXCL_LINE
                fi
                cp -R "$LOCAL_ATTIC_DIR/$io_name" "$child_dir_path"
            else
                die "The step '$step_name' expects '$LOCAL_ATTIC_DIR/$io_name' to have been created by a previous step but it does not exist" # LCOV_EXCL_LINE
            fi
        done
    fi
}

function simulate_dirs_after() {
    step_name=$1
    say "==> Finishing: $step_name"
    cd "$original_current_dir"

    input_dirs=$(jq  -r ".steps.\"$step_name\".inputDirs|@sh"  < $STEP_CONFIG_FILE)
    output_dirs=$(jq  -r ".steps.\"$step_name\".outputDirs|@sh"  < $STEP_CONFIG_FILE)

    [[ $step_name == 'local-create-book-directory' ]] && output_dirs='INPUT_SOURCE_DIR'
    [[ $step_name == 'look-up-book' ]] && output_dirs='INPUT_SOURCE_DIR IO_BOOK'

    # Copy output directories into the attic (for use by later steps)
    if [[ $output_dirs != null ]]; then
        [[ -d $LOCAL_ATTIC_DIR ]] || mkdir -p $LOCAL_ATTIC_DIR # create dir if does not exist

        for io_name in $output_dirs; do
            io_name=$(echo $io_name | tr -d "'")  # unquote from jq
            pointer=$io_name # https://stackoverflow.com/a/55331060
            child_dir_path="${!pointer}"

            if [[ -d "$LOCAL_ATTIC_DIR/$io_name" ]]; then
                rm -rf "$LOCAL_ATTIC_DIR/$io_name"
            fi 
            mv "$child_dir_path" "$LOCAL_ATTIC_DIR/$io_name"
        done
    fi

    # Remove any input-only directories
    if [[ $input_dirs != null ]]; then
        for io_name in $input_dirs; do
            io_name=$(echo $io_name | tr -d "'")  # unquote from jq
            pointer=$io_name # https://stackoverflow.com/a/55331060
            child_dir_path="${!pointer}"

            rm -rf "$child_dir_path"
        done
    fi
 
}

# Try to find if the command is in the pipeline first
first_arg=$1
pipeline_steps=$(jq -r ".pipelines.\"$first_arg\"|@sh" < $STEP_CONFIG_FILE)

if [[ $first_arg == local-create-book-directory ]]; then
    do_step_named local-create-book-directory "${@:2}"
elif [[ $pipeline_steps = 'null' ]]; then
    do_step_named $(echo $first_arg | tr -d "'")
else
    do_step_named local-create-book-directory "${@:2}"
    do_step_named look-up-book
    
    for step_name in $pipeline_steps; do
        do_step_named $(echo $step_name | tr -d "'")
    done
fi
