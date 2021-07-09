parse_book_dir

if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
    try link-single "${IO_BAKED}" "${IO_BAKE_META}" "${ARG_TARGET_SLUG_NAME}" "${IO_LINKED}/${ARG_TARGET_SLUG_NAME}.linked.xhtml" --mock-otherbook # LCOV_EXCL_LINE
else
    try link-single "${IO_BAKED}" "${IO_BAKE_META}" "${ARG_TARGET_SLUG_NAME}" "${IO_LINKED}/${ARG_TARGET_SLUG_NAME}.linked.xhtml"
fi
