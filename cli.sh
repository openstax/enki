#!/usr/bin/env bash

# Wraps the docker execution in a nice bow

set -e

image_name=my_image
book_name=$1

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


if [[ ${book_name} == 'shell' ]]
then
    docker build -t ${image_name} .
    docker run -it --rm ${image_name} /bin/bash
    exit $?
fi

local_dir=$(pwd)/data/${book_name}/

[[ ${book_name} ]] || ( >&2 echo "ERROR: A book name is required as the first argument" && exit 111)
[[ $2 ]] || ( >&2 echo "ERROR: A command is required as the second argument" && exit 111)

docker build -t ${image_name} .
docker run -it -v ${local_dir}:/data/ -e GH_SECRET_CREDS--rm ${image_name} "${@:2}" # Args after the 1st one

if [[ $2 == *pdf ]]
then
    >&2 echo "The PDF is available at ${local_dir}/assembled/collection.pdf"
fi