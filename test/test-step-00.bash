#!/bin/bash
set -e
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"
[[ ${TRACE_ON} ]] && set -x

cd ../build-concourse/
npm install

# Build concourse pipelines with dummy credentials just to make sure it runs
CODE_VERSION=dummycodeversion \
AWS_ACCESS_KEY_ID=dummyawskey \
AWS_SECRET_ACCESS_KEY=dummyawssecret \
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS=dummygoogle \
npm run coverage
