#!/bin/bash

# Files
out_file='script/cross-lib/book_data/AUTO_books.txt'
ubl='script/cross-lib/book_data/USER_ubl.txt'
mkdir -p 'script/cross-lib/book_data'; touch $out_file; touch $ubl

# Refresh ABL
abl="$(curl -Ss 'https://raw.githubusercontent.com/openstax/content-manager-approved-books/main/approved-book-list.json')"
query=$(cat << 'EOF'
  .approved_books
  | .[]
  | .repository_name as $repo
  | .versions[0].commit_metadata.books
  | .[]
  | $repo + " " + .slug
EOF
)
echo "$abl" | jq -r "$query" > $out_file

# Add ubl
cat $ubl >> $out_file

# TODO: remove doubles
