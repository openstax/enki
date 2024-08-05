#!/bin/sh
set -e
cd "$(dirname "$0")"

# Verify the Dockerfile is committed into git
if [ -n "$CI_TEST" ]; then
    git diff-index --quiet HEAD
fi

TRACE_ON=$TRACE_ON ./test/test-step-00.bash
TRACE_ON=$TRACE_ON ./test/test-step-01.bash
TRACE_ON=$TRACE_ON ./test/test-step-02.bash
TRACE_ON=$TRACE_ON ./test/test-step-03.bash
TRACE_ON=$TRACE_ON ./test/test-step-05.bash
TRACE_ON=$TRACE_ON ./test/test-step-06.bash
TRACE_ON=$TRACE_ON ./test/test-step-07.bash
TRACE_ON=$TRACE_ON ./test/test-step-11.bash
TRACE_ON=$TRACE_ON ./test/test-step-08.bash
TRACE_ON=$TRACE_ON ./test/test-step-09.bash
TRACE_ON=$TRACE_ON ./test/test-step-12.bash
