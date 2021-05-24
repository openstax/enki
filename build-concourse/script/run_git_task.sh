exec > >(tee $IO_COMMON_LOG/log >&2) 2>&1

[[ $TASK_NAME ]] || (echo "Did not specify a TASK_NAME to run" && exit 1)
[[ -d $IO_COMMON_LOG ]] || (echo "Undefined Environment variable: IO_COMMON_LOG" && exit 1)
[[ -d $IO_BOOK ]] || (echo "Undefined Environment variable: IO_BOOK" && exit 1)
[[ -f ./$IO_BOOK/repo ]] || (echo "Expected to see a repo file since this is a git task" && exit 1)
[[ $PDF_OR_WEB ]] || (echo "Undefined Environment variable: PDF_OR_WEB" && exit 1)
[[ $CODE_VERSION ]] || (echo "Undefined Environment variable: CODE_VERSION" && exit 1)


export ARG_RECIPE_NAME="$(cat ./$IO_BOOK/style)"
export ARG_GIT_REF="$(cat ./$IO_BOOK/version)"

export ARG_REPO_NAME="$(cat ./$IO_BOOK/repo)"
export ARG_TARGET_SLUG_NAME="$(cat ./$IO_BOOK/slug)"

if [[ -f ./$IO_BOOK/pdf_filename ]]; then
    export ARG_TARGET_PDF_FILENAME="$(cat ./$IO_BOOK/pdf_filename)"
fi

# These are just mapped because the script prefixes args with ARG_
export ARG_CODE_VERSION=$CODE_VERSION
export ARG_S3_BUCKET_NAME=$CORGI_ARTIFACTS_S3_BUCKET

TRACE_ON=1 docker-entrypoint.sh $TASK_NAME
