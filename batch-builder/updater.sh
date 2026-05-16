#!/bin/bash

# Run this to update the book list without having ruby installed.
root_dir=batch-builder
docker build --tag batch-builder --file $root_dir/Dockerfile.ruby_env $root_dir/.
docker run \
  --rm -it \
  --mount type=bind,source=$(pwd)/batch-builder,target=/code/batch-builder \
  --name batch-builder-builder \
  batch-builder \
  $root_dir/update_books.rb
