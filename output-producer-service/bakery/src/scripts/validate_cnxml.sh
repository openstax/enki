#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

case $CONTENT_SOURCE in
archive)
  collection_id="$(cat "${BOOK_INPUT}/collection_id")"
  collections="${INPUT_SOURCE}/$collection_id/${COLLECTIONS_PATH}"
  modules="${INPUT_SOURCE}/$collection_id/${MODULES_PATH}"
  ;;
git)
  collections="${INPUT_SOURCE}/${COLLECTIONS_PATH}"
  modules="${INPUT_SOURCE}/${MODULES_PATH}"
  ;;
*)
  echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
  exit 1
  ;;
esac

# Validate collections and modules without failing fast
failure=false

# The shellcheck disables that follow are due to desired / expected globbing
# shellcheck disable=SC2086
validate-collxml $collections || failure=true
# shellcheck disable=SC2086
validate-cnxml $modules || failure=true

if $failure; then
  exit 1
fi
