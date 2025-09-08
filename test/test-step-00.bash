#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

# Use --prefix to keep the .nyc_output at the root for codecov
npm --prefix ../build-concourse/ install

# Build concourse pipelines with dummy credentials just to make sure it runs
CODE_VERSION=dummycodeversion \
AWS_ACCESS_KEY_ID=dummyawskey \
AWS_SECRET_ACCESS_KEY=dummyawssecret \
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS=dummygoogle \
ANCILLARIES_HOST=dummyancillarieshost \
ANCILLARY_TYPE_CONFIG=dummyancillariesconfig \
npm --prefix ../build-concourse/ run coverage


# Make the LCOV file absolute so codecov understands it
sed -i.bak "s@SF:@SF:$(cd ../build-concourse;pwd)/@" ../coverage/lcov.info


npm --prefix ../bakery-js/ install
npm --prefix ../bakery-js/ test
