#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

if [[ $CI = '' && $VIRTUAL_ENV = '' ]]; then
   echo "ERROR: Activate a virtualenv before running this"
   exit 1
fi

pip install "../bakery-src/scripts/.[test]"
flake8 --config ../bakery-src/.flake8 ../bakery-src/scripts

pytest --asyncio-mode=strict --cov=bakery_scripts --cov-append --cov-report=xml:cov.xml --cov-report=html:cov.html --cov-report=term-missing  ../bakery-src -vvv
sed -i 's/filename=".*\/bakery_scripts/filename="/g' cov.xml

# Upload to codecov only if running inside CI
if [[ $CI || $CODECOV_TOKEN ]]; then
   echo "Upload Code Coverage Results!"
   curl -Os https://uploader.codecov.io/latest/linux/codecov && chmod +x codecov && ./codecov  -t ${CODECOV_TOKEN} -f cov.xml
fi
