#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

shopt -s globstar nullglob
for collection in "${RAW_COLLECTION_DIR}/collections/"*; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "${TARGET_BOOK}" ]]; then
        if [[ "$slug_name" != "${TARGET_BOOK}" ]]; then
            continue
        fi
    fi
    mv "$collection" "${RAW_COLLECTION_DIR}/modules/collection.xml"

    neb assemble "${RAW_COLLECTION_DIR}/modules" temp-assembly/

    cp "temp-assembly/collection.assembled.xhtml" "${ASSEMBLED_OUTPUT}/$slug_name.assembled.xhtml"
    rm -rf temp-assembly
done
shopt -u globstar nullglob
