#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

jsonify "${DISASSEMBLED_INPUT}" "${JSONIFIED_OUTPUT}"
jsonschema -i "${JSONIFIED_OUTPUT}/$(cat "${BOOK_INPUT}/slug").toc.json" /code/scripts/book-schema-git.json

for jsonfile in "${JSONIFIED_OUTPUT}/"*@*.json; do
    jsonschema -i "$jsonfile" /code/scripts/page-schema.json
done
