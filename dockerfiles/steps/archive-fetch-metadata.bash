try wget "$ABL_FILE_URL" -O "$IO_ARCHIVE_FETCHED/approved-book-list.json"

# Verify the ABL schema version is what subsequent tasks expect
EXPECTED_ABL_VER=2
ABL_SCHEMA_VER=$(jq '.api_version' < "$IO_ARCHIVE_FETCHED/approved-book-list.json")
if [[ $ABL_SCHEMA_VER != "$EXPECTED_ABL_VER" ]]; then
    die "Subsequent steps assume ABL version $EXPECTED_ABL_VER but the actual is $ABL_SCHEMA_VER" # LCOV_EXCL_LINE
fi
