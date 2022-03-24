#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

pip install "../output-producer-service/bakery/src/scripts/.[test]"
flake8 "../output-producer-service/bakery/src/scripts" --max-line-length=100

pytest --cov=bakery_scripts --cov-append --cov-report=xml:cov.xml --cov-report=html:cov.html --cov-report=term --cov=../output-producer-service/bakery/src/tests -vvv

# Upload to codecov only if running inside CI
if [[ $CI || $CODECOV_TOKEN ]]; then
   echo "Upload Code Coverage Results!"
   curl -Os https://uploader.codecov.io/latest/linux/codecov && chmod +x codecov && ./codecov  -t ${CODECOV_TOKEN} -f cov.xml
fi
