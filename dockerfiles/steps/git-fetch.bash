parse_book_dir
[[ "$ARG_GIT_REF" == latest ]] && ARG_GIT_REF=main
[[ "$ARG_REPO_NAME" == */* ]] || ARG_REPO_NAME="openstax/$ARG_REPO_NAME"

creds_dir=$(pwd)/tmp-gh-creds

# Support sideloading the book
if [[ $LOCAL_SIDELOAD_REPO_PATH && -d $LOCAL_SIDELOAD_REPO_PATH ]]; then
    [[ -d $IO_FETCHED ]] && rm -rf "$IO_FETCHED" # LCOV_EXCL_LINE
    warn "-----------------------------------" # LCOV_EXCL_LINE
    warn "Sideloading book instead of cloning" # LCOV_EXCL_LINE
    warn "-----------------------------------" # LCOV_EXCL_LINE
    try cp -r $LOCAL_SIDELOAD_REPO_PATH "$IO_FETCHED" # LCOV_EXCL_LINE
elif [[ -d "$IO_FETCHED/.git" ]]; then # Skip if we already cloned (dev)
    warn "---------------------------------------------------" # LCOV_EXCL_LINE
    warn "Skipping git clone because directory already exists" # LCOV_EXCL_LINE
    warn "---------------------------------------------------" # LCOV_EXCL_LINE
else
    remote_url="https://github.com/$ARG_REPO_NAME.git"

    # kcov barfs when "set -x" is called so we just skip all of this authentication
    if [[ $KCOV_DIR == '' ]]; then
        # LCOV_EXCL_START
        # Do not show creds
        set +x
        if [[ $GH_SECRET_CREDS ]]; then
            creds_file="$creds_dir/gh-creds"
            git config --global credential.helper "store --file=$creds_file"
            mkdir --parents "$creds_dir"
            echo "https://$GH_SECRET_CREDS@github.com" > "$creds_file" 2>&1
        else
            echo "--------------------------------------------------------"
            echo "Warning: GH_SECRET_CREDS is not set to anything."
            echo "   This is only necessary for private repos."
            echo "   If you get an error cloning, this might be the cause."
            echo "--------------------------------------------------------"
        fi
        [[ $TRACE_ON ]] && set -x
        # LCOV_EXCL_END
    fi

    # If ARG_GIT_REF starts with '@' then it is a commit and check out the individual commit
    # Or, https://stackoverflow.com/a/7662531
    [[ $ARG_GIT_REF =~ ^[a-f0-9]{40}$ ]] && ARG_GIT_REF="@$ARG_GIT_REF"

    if [[ $ARG_GIT_REF = @* ]]; then
        # Steps to try:
        # 1. Try a shallow clone (50 most recent commits on the main branch)
        # 2. Try including branches (maybe it's an old edition?)
        # 3. Upgrade to a deep clone
        git_commit="${ARG_GIT_REF:1}"

        GIT_TERMINAL_PROMPT=0 try git clone --depth 50 "$remote_url" "$IO_FETCHED"
        try pushd "$IO_FETCHED"

        set +e
        git reset --hard "$git_commit"
        commit_not_found=$?
        set -e

        # If the commit was not recent, try fetching all the branches
        if [[ $commit_not_found != 0 ]]; then

            try git remote set-branches origin '*'
            GIT_TERMINAL_PROMPT=0 try git fetch -v

            set +e
            git reset --hard "$git_commit"
            commit_not_found=$?
            set -e

            # If the commit was not in the branches, convert the shallow clone to a deep clone
            # LCOV_EXCL_START
            if [[ $commit_not_found != 0 ]]; then
                GIT_TERMINAL_PROMPT=0 try git fetch --unshallow # convert shallow clone to deep clone
                try git reset --hard "$git_commit"
            fi
            # LCOV_EXCL_END
        fi
        try popd
    else
        GIT_TERMINAL_PROMPT=0 try git clone --depth 1 "$remote_url" --branch "$ARG_GIT_REF" "$IO_FETCHED"
    fi
fi

# Clean up the temporary credentials file if it exists
if [[ -f $creds_dir ]]; then
    try rm -rf $creds_dir # LCOV_EXCL_LINE
fi

# If the user wants to build one book then check that the book exists
# so we can error early.
if [[ $ARG_TARGET_SLUG_NAME ]]; then
    manifest_file="$IO_FETCHED/META-INF/books.xml"
    set +e
    book_slugs=$(try xmlstarlet sel -t --match '//*[@slug]' --value-of '@slug' < $manifest_file)
    book_href=$(try xmlstarlet sel -t --match "//*[@slug=\"$ARG_TARGET_SLUG_NAME\"]" --value-of '@href' < $manifest_file)
    set -e
    [[ $book_href ]] || die "META-INF/books.xml is missing an entry for slug='$ARG_TARGET_SLUG_NAME'. Valid slugs: $book_slugs" # LCOV_EXCL_LINE
fi