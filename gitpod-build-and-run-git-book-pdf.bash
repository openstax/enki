#!/bin/bash
set -e

if [[ ! $GITPOD_HOST && ! $VIRTUAL_ENV ]]; then
    echo -e 'Not running in a virtual environment or inside gitpod. This script will install python packages globally so exiting just to be safe.'
    exit 1
fi

# This is essentially each step in the Dockerfile.common but without the COPY lines.


./dockerfiles/build/build-system-venv.sh
source ./dockerfiles/build/build-system-node.env
./dockerfiles/build/build-stage-mathify.sh
./dockerfiles/build/build-stage-neb-3rdparty.bash
./dockerfiles/build/build-stage-neb-install.bash
./dockerfiles/build/build-stage-bakery-3rdparty.bash
./dockerfiles/build/build-stage-bakery-install.bash
./dockerfiles/build/build-stage-xhtmlvalidator.sh


# Load all the environment vars that point to the input/output dirs for each step
set -o allexport
source ./gitpod.env
set +o allexport

[ -d ./data ] && rm -rf ./data
mkdir ./data

TRACE_ON=1 ./dockerfiles/docker-entrypoint.sh all-pdf philschatz/tiny-book/book-slug1 chemistry main