#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

# FIXME: We assume that every book in the group uses the same style
# This assumption will not hold true forever, and book style + recipe name should
# be pulled from fetched-book-group (while still allowing injection w/ CLI)

# FIXME: Style devs will probably not like having to bake multiple books repeatedly,
# especially since they shouldn't care about link-extras correctness during their
# work cycle.

# FIXME: Separate style injection step from baking step. This is way too much work to change a line injected into the head tag
style_file="cnx-recipes-output/rootfs/styles/$(cat "${BOOK_INPUT}"/style)-pdf.css"

if [[ -f "$style_file" ]]
    then
        cp "$style_file" "${BAKED_OUTPUT}"
        cp "$style_file" "${STYLE_OUTPUT}"
    else
        echo "Warning: Style Not Found" > "${BAKED_OUTPUT}/stderr"
fi

shopt -s globstar nullglob
for collection in "${ASSEMBLED_INPUT}/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "${TARGET_BOOK}" ]]; then
        if [[ "$slug_name" != "${TARGET_BOOK}" ]]; then
            continue
        fi
    fi
    /code/bake_root -b "$(cat "${BOOK_INPUT}"/style)" -r cnx-recipes-output/rootfs/recipes -i "${ASSEMBLED_INPUT}/$slug_name.assembled.xhtml" -o "${BAKED_OUTPUT}/$slug_name.baked.xhtml"
    if [[ -f "$style_file" ]]
        then
            sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename "$style_file")\" />&%" "${BAKED_OUTPUT}/$slug_name.baked.xhtml"
    fi
done
shopt -u globstar nullglob
