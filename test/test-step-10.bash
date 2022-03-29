#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

if [[ $CI = '' && $VIRTUAL_ENV = '' ]]; then
   echo "ERROR: Activate a virtualenv before running this"
   exit 1
fi

pip install "../output-producer-service/bakery/src/scripts/.[test]"
flake8 "../output-producer-service/bakery/src/scripts" --max-line-length=110

pytest --cov=bakery_scripts --cov-append --cov-report=xml:cov.xml --cov-report=html:cov.html --cov-report=term  ../output-producer-service -vvv
sed -i 's/filename=".*\/bakery_scripts/filename="/g' cov.xml

# Upload to codecov only if running inside CI
if [[ $CI || $CODECOV_TOKEN ]]; then
   echo "Upload Code Coverage Results!"
   curl -Os https://uploader.codecov.io/latest/linux/codecov && chmod +x codecov && ./codecov  -t ${CODECOV_TOKEN} -f cov.xml
fi
