#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"


if [[ ! $CI && ! $VIRTUAL_ENV ]]; then
    echo "ERROR: Activate a virtualenv before running this"
    exit 1
fi

pushd ../corgi-concourse-resource
    pip install '.[test]'
    pytest \
        --cov=corgi_concourse_resource \
        --cov-append \
        --cov-report=xml:../test/cov.xml \
        --cov-report=html:../test/cov.html \
        --cov-report=term  \
        -vvv
popd
