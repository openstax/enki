exec > >(tee $IO_COMMON_LOG/log >&2) 2>&1

[[ $TASK_NAME ]] || { echo "Did not specify a TASK_NAME to run"; exit 1; }
[[ -d $IO_COMMON_LOG ]] || { echo "Undefined Environment variable: IO_COMMON_LOG"; exit 1; }
[[ -d $IO_BOOK ]] || { echo "Undefined Environment variable: IO_BOOK"; exit 1; }
[[ $CODE_VERSION ]] || { echo "Undefined Environment variable: CODE_VERSION"; exit 1; }

# These are just mapped because the script prefixes args with ARG_
export ARG_CODE_VERSION=$CODE_VERSION
export ARG_S3_BUCKET_NAME=${CORGI_ARTIFACTS_S3_BUCKET:-$WEB_S3_BUCKET}

TRACE_ON=1 docker-entrypoint.sh $TASK_NAME
