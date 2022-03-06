#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

shopt -s globstar nullglob
# Create an empty map file for invoking assemble-meta
echo "{}" > uuid-to-revised-map.json
for collection in "${ASSEMBLED_INPUT}/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "${TARGET_BOOK}" ]]; then
        if [[ "$slug_name" != "${TARGET_BOOK}" ]]; then
            continue
        fi
    fi
    assemble-meta "${ASSEMBLED_INPUT}/$slug_name.assembled.xhtml" uuid-to-revised-map.json "${OUTPUT_NAME}/${slug_name}.assembled-metadata.json"
done
shopt -u globstar nullglob
