#!/bin/bash
set -e
HERE="$(cd "$(dirname "$0")"; pwd)"
[[ $TRACE_ON ]] && set -x


pushd corgi-concourse-resource >/dev/null
make lint
make test TEST_EXTRA_ARGS="--cov-append --cov-report=xml:$HERE/cov.xml --cov-report=html:$HERE/cov.html"
popd >/dev/null
