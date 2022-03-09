#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

slug_name=$(cat "${BOOK_INPUT}/slug")
disassemble "${RESOURCE_LINKED_INPUT}/$slug_name.linked.xhtml" "${BAKED_BOOK_META_INPUT}/$slug_name.baked-metadata.json" "$slug_name" "${DISASSEMBLED_OUTPUT}"
