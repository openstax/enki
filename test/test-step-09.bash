#!/bin/bash
set -e
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"
[[ ${TRACE_ON} ]] && set -x

# Lint the bash scripts
shellcheck --severity=warning ../dockerfiles/steps/* ../dockerfiles/build/*
