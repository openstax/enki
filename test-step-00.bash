#!/bin/bash
set -e

echo "WARN: Book Disassembly hangs without making a tweak. Comment a few lines and try again. See https://github.com/openstax/output-producer-service/pull/372"
sleep 10

# Draw the dependency graph PNG files
cd ./build-concourse/
npm install
npm run draw-graphs

# Build concourse pipelines with dummy credentials just to make sure it runs
CODE_VERSION=dummycodeversion \
AWS_ACCESS_KEY_ID=dummyawskey \
AWS_SECRET_ACCESS_KEY=dummyawssecret \
npm start
