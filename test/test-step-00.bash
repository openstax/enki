#!/bin/bash
set -e
[[ ${TRACE_ON} ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

# Use --prefix to keep the .nyc_output at the root for codecov
npm --prefix ../build-concourse/ install

# Build concourse pipelines with dummy credentials just to make sure it runs
CODE_VERSION=dummycodeversion \
AWS_ACCESS_KEY_ID=dummyawskey \
AWS_SECRET_ACCESS_KEY=dummyawssecret \
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS=dummygoogle \
npm --prefix ../build-concourse/ run coverage

# Move so codecov finds it
mv ../build-concourse/.nyc_output ../