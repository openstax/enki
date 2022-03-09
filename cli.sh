#!/bin/bash

set -e

# Example:
# ./cli.sh ./data/tin-bk/   all-git-pdf 'philschatz/tiny-book/book-slug1' chemistry main

[[ $1 ]] && data_dir="--data-dir $1"
[[ $2 ]] && command="--command $2"
[[ $3 ]] && {
    # This could still technically be an archive collection id
    this_arg=$3
    book_slug="${this_arg##*/}"
    repo_name="${this_arg%/*}"
    if [[ $book_slug ]]; then
        repo="--repo $repo_name --book-slug $book_slug"
    else
        repo="--repo $this_arg"
    fi
}
[[ $4 ]] && style="--style $4"
[[ $5 ]] && ref="--ref $5"

echo '****************'
echo '** DEPRECATED **'
echo '****************'
echo ''
echo 'Use the enki script directly.'
echo '- you can run the enki script from any directory'
echo '- you can create a symbolic link to it'
echo '- you no longer need to cd into this directory before running the script'
echo ''
echo 'Here is the enki command you should run instead:'
echo "./enki $data_dir $command $repo $style $ref"
echo ''
echo 'Sleeping for 2 minutes...'
sleep 120

./enki $data_dir $command $repo $style $ref