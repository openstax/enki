#!/bin/bash
set -e
[[ ${TRACE_ON} ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

# Lint the bash scripts
shellcheck --severity=warning ../dockerfiles/steps/* ../dockerfiles/build/*
