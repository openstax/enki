#!/bin/bash

# Run this to update the book list without having ruby installed.
root_dir=cross-lib
docker build --tag cross-lib --file $root_dir/Dockerfile.ruby_env $root_dir/.
docker run \
  --rm -it \
  --mount type=bind,source=$(pwd)/cross-lib,target=/code/cross-lib \
  --name cross-lib-builder \
  cross-lib \
  $root_dir/update_books.rb
