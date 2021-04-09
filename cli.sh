#!/usr/bin/env bash

# Wraps the docker execution in a nice bow

set -e

book_name=$1

local_dir=$(pwd)/data/${book_name}/

[[ ${book_name} ]] || ( >&2 echo "ERROR: A book name is required as the first argument" && exit 111)
[[ $2 ]] || ( >&2 echo "ERROR: A command is required as the second argument" && exit 111)

docker build -t my_image .
docker run -it -v ${local_dir}:/data/ --rm my_image "${@:2}" # Args after the 1st one

if [[ $2 == 'pdf' ]]
then
    >&2 echo "The PDF is available at ${local_dir}/assembled/collection.pdf"
fi