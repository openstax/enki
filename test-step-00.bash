#!/bin/bash
set -e

cd ./build-concourse/
npm install

# Build concourse pipelines with dummy credentials just to make sure it runs
CODE_VERSION=dummycodeversion \
AWS_ACCESS_KEY_ID=dummyawskey \
AWS_SECRET_ACCESS_KEY=dummyawssecret \
npm start

CODE_VERSION=dummycodeversion \
AWS_ACCESS_KEY_ID=dummyawskey \
AWS_SECRET_ACCESS_KEY=dummyawssecret \
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS=dummygoogle \
npm run build-gdocs

# Fail if anything is not committed
if [[ $CI_TEST ]]; then
    git diff
    git diff-index --quiet HEAD
fi

# Draw the dependency graph PNG files (these will cause bit-jitter)
npm run draw-graphs
