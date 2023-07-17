#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

if [[ $CI = '' && $VIRTUAL_ENV = '' ]]; then
   echo "ERROR: Activate a virtualenv before running this"
   exit 1
fi


# More details: https://github.com/aws/aws-cli/issues/8036#issuecomment-1638544754
# and: https://github.com/yaml/pyyaml/issues/601
# PyYAML installed as dependency here [awscli](https://github.com/aws/aws-cli/blob/dbbf1ce01acec0116710968bbe5a96680e791c1b/setup.py#L30)
pip install "PyYAML==5.3.1" "../bakery-src/scripts/.[test]"
flake8 "../bakery-src/scripts" --max-line-length=110

pytest --asyncio-mode=strict --cov=bakery_scripts --cov-append --cov-report=xml:cov.xml --cov-report=html:cov.html --cov-report=term-missing  ../bakery-src -vvv
sed -i 's/filename=".*\/bakery_scripts/filename="/g' cov.xml

# Upload to codecov only if running inside CI
if [[ $CI || $CODECOV_TOKEN ]]; then
   echo "Upload Code Coverage Results!"
   curl -Os https://uploader.codecov.io/latest/linux/codecov && chmod +x codecov && ./codecov  -t ${CODECOV_TOKEN} -f cov.xml
fi
