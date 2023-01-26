#!/usr/bin/env ruby

require 'json'

# Files
out_file = 'bap/book_data/AUTO_books.txt'
ubl = 'bap/book_data/USER_ubl.txt'
`mkdir -p bap/book_data; touch #{out_file}; touch #{ubl}`

# Refresh ABL (bash)
abl_hash = JSON.parse(
  `curl -Ss https://raw.githubusercontent.com/openstax/content-manager-approved-books/main/approved-book-list.json`
)

# Write ABL
File.delete(out_file)
abl_hash['approved_books'].each do |book|
  repo = book['repository_name']
  book['versions'][0]['commit_metadata']['books'].each do |volume| 
    File.write(out_file, "#{repo} #{volume['slug']}\n", mode: 'a')
  end
end

# Write unapproved books
if File.exist?(ubl)
  File.readlines(ubl).each do |line|
    File.write(out_file, line, mode: 'a')
  end
end