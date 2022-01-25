#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

# Lint the bash scripts
if [[ $(command -v shellcheck) ]]; then
    shellcheck --severity=warning ../dockerfiles/steps/* ../dockerfiles/build/*
else
    echo "Warning: Linting failed, shellcheck not found"
fi
