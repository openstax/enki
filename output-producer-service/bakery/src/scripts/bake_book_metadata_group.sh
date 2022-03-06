#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

shopt -s globstar nullglob
for collection in "${BAKED_INPUT}/"*.baked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "${TARGET_BOOK}" ]]; then
        if [[ "$slug_name" != "${TARGET_BOOK}" ]]; then
            continue
        fi
    fi

    bake-meta "${ASSEMBLED_META_INPUT}/$slug_name.assembled-metadata.json" "${BAKED_INPUT}/$slug_name.baked.xhtml" "" "" "${BAKED_META_OUTPUT}/$slug_name.baked-metadata.json"
done
shopt -u globstar nullglob
