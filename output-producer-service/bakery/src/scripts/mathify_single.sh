#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

slug_name=$(cat "${BOOK_INPUT}/slug")

# Style needed because mathjax will size converted math according to surrounding text
cp "${STYLE_INPUT}"/* "${LINKED_INPUT}"

node /src/typeset/start -i "${LINKED_INPUT}/$slug_name.linked.xhtml" -o "${MATHIFIED_OUTPUT}/$slug_name.mathified.xhtml" -f svg
