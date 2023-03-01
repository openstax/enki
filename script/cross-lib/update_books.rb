#!/usr/bin/env ruby

require 'json'
require 'set'

# Files
out_file = 'bap/book_data/AUTO_books.txt'
ubl = 'bap/book_data/USER_ubl.txt'
`mkdir -p bap/book_data; touch #{out_file}; touch #{ubl}`

# Refresh ABL (bash)
abl_hash = JSON.parse(
  `curl -Ss https://raw.githubusercontent.com/openstax/content-manager-approved-books/main/approved-book-list.json`
)

books=Set[]
# Write ABL
abl_hash['approved_books'].each do |book|
  repo = book['repository_name']
  book['versions'][0]['commit_metadata']['books'].each do |volume| 
    books.add("#{repo} #{volume['slug']}\n")
  end
end

# Write unapproved books
if File.exist?(ubl)
  File.readlines(ubl).each do |line|
    books.add(line)
  end
end

# Add files
File.delete(out_file)
books.each do |book|
  File.write(out_file, book, mode: 'a')
end
