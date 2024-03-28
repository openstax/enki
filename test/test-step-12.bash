#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

install_poetry() {
    pip install 'poetry==1.4.0'
}

if [[ $CI ]]; then
    install_poetry
elif [[ ! $(which poetry) ]]; then
    if [[ ! $VIRTUAL_ENV ]]; then
        echo "ERROR: Activate a virtualenv before running this"
        exit 1
    else
        install_poetry
    fi
fi

pushd ../corgi-concourse-resource
    poetry install
    poetry run pytest \
        --cov=corgi_concourse_resource \
        --cov-append \
        --cov-report=xml:../test/cov.xml \
        --cov-report=html:../test/cov.html \
        --cov-report=term  \
        -vvv
popd

# Upload to codecov only if running inside CI
if [[ $CI || $CODECOV_TOKEN ]]; then
   echo "Upload Code Coverage Results!"
   curl -Os https://uploader.codecov.io/latest/linux/codecov && chmod +x codecov && ./codecov  -t ${CODECOV_TOKEN} -f cov.xml
fi
