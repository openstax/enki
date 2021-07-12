parse_book_dir
[[ "${ARG_GIT_REF}" == latest ]] && ARG_GIT_REF=main
[[ "${ARG_REPO_NAME}" == */* ]] || ARG_REPO_NAME="openstax/${ARG_REPO_NAME}"

remote_url="https://github.com/${ARG_REPO_NAME}.git"

if [[ ${GH_SECRET_CREDS} ]]; then
    # LCOV_EXCL_START
    creds_dir=tmp-gh-creds
    creds_file="$creds_dir/gh-creds"
    git config --global credential.helper "store --file=$creds_file"
    mkdir "$creds_dir"
    # Do not show creds
    set +x
    echo "https://$GH_SECRET_CREDS@github.com" > "$creds_file" 2>&1
    [[ $TRACE_ON ]] && set -x
    # LCOV_EXCL_STOP
fi

# If ARG_GIT_REF starts with '@' then it is a commit and check out the individual commit
# Or, https://stackoverflow.com/a/7662531
[[ ${ARG_GIT_REF} =~ ^[a-f0-9]{40}$ ]] && ARG_GIT_REF="@${ARG_GIT_REF}"

if [[ ${ARG_GIT_REF} = @* ]]; then
    # LCOV_EXCL_START
    git_commit="${ARG_GIT_REF:1}"
    GIT_TERMINAL_PROMPT=0 try git clone --depth 50 "${remote_url}" "${IO_FETCHED}"
    try pushd "${IO_FETCHED}"
    try git reset --hard "${git_commit}"
    # If the commit was not recent, try cloning the whole repo
    if [[ $? != 0 ]]; then
        try popd
        GIT_TERMINAL_PROMPT=0 try git clone "${remote_url}" "${IO_FETCHED}"
        try pushd "${IO_FETCHED}"
        try git reset --hard "${git_commit}"
    fi
    try popd
    # LCOV_EXCL_STOP
else
    GIT_TERMINAL_PROMPT=0 try git clone --depth 1 "${remote_url}" --branch "${ARG_GIT_REF}" "${IO_FETCHED}"
fi

if [[ ! -f "${IO_FETCHED}/collections/${ARG_TARGET_SLUG_NAME}.collection.xml" ]]; then
    die "No matching book for slug in this repo" # LCOV_EXCL_LINE
fi
