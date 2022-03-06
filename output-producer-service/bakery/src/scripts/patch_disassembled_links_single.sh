#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

slug_name=$(cat "${BOOK_INPUT}/slug")
patch-same-book-links "${DISASSEMBLED_INPUT}" "${DISASSEMBLED_LINKED_OUTPUT}" "$slug_name"
cp "${DISASSEMBLED_INPUT}"/*@*-metadata.json "${DISASSEMBLED_LINKED_OUTPUT}"
cp "${DISASSEMBLED_INPUT}"/"$slug_name".toc* "${DISASSEMBLED_LINKED_OUTPUT}"
