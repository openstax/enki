#!/usr/bin/env bash

# Wraps the docker execution in a nice bow

set -e

# Trace if TRACE_ON is set
[[ ${TRACE_ON} ]] && set -x

image_name=my_image
local_dir=$1

# Books use more memory than Docker's default. Check if it is low and inform the user
hyperkit_file="${HOME}/Library/Containers/com.docker.docker/Data/vms/0/hyperkit.json"
if [[ -f "${hyperkit_file}" ]]
then
    too_small=0

    # If jq is installed then we can use it
    if [[ $(command -v jq) ]]
    then
        memory_size=$(jq .memory < "${hyperkit_file}")
        [[ ! ${memory_size} > 2048 ]] && too_small=1
    else
        # Otherwise, just use a string search and hope that we find it
        [[ $(grep '"memory":2048,' "${hyperkit_file}") != '' ]] && too_small=1
    fi

    if [[ ${too_small} == 1 ]]
    then
        >&2 echo ""
        >&2 echo "===================================================================="
        >&2 echo "WARNING: Docker seems to be configured for a small amount of memory."
        >&2 echo "Consider expanding it by following the instructions here:"
        >&2 echo "  https://docs.docker.com/docker-for-windows/#resources"
        >&2 echo "===================================================================="
        sleep 5
    fi
fi

[[ ${local_dir} ]] || ( >&2 echo "ERROR: A local temp directory for the book is required as the first argument" && exit 111)
[[ $2 ]] || ( >&2 echo "ERROR: A command is required as the second argument" && exit 111)

# Ensure the directory is created with the current user so docker can chown its files to be the same user
[[ -d ${local_dir} ]] || mkdir "${local_dir}"

docker build -t ${image_name} .
docker run -it -v $(cd "${local_dir}"/; pwd):/data/ \
    -e GH_SECRET_CREDS \
    -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY \
    -e AWS_SESSION_TOKEN \
    -e TRACE_ON \
    --rm ${image_name} "${@:2}" # Args after the 1st one

if [[ $2 == *pdf ]]
then
    >&2 echo "The PDF is available somewhere in either ${local_dir}/assembled/collection.pdf or ${local_dir}/artifacts-single/"
fi