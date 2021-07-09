# Validate collections and modules without failing fast
failure=false

# The shellcheck disables that follow are due to desired / expected globbing
# shellcheck disable=SC2086
validate-collxml $IO_ARCHIVE_FETCHED/collection.xml || failure=true
# shellcheck disable=SC2086
validate-cnxml $IO_ARCHIVE_FETCHED/**/index.cnxml || failure=true

if $failure; then
    exit 1 # LCOV_EXCL_LINE
fi
