#!/bin/sh
set -e

cd $PROJECT_ROOT/cookbook
gem install bundler --no-document
gem install byebug --no-document
# TODO: Find a better way to install these. They were in install_used_gem_versions
gem install nokogiri --no-document
gem install slop --no-document

bundle config set no-cache 'true'
bundle config set silence_root_warning 'true'

# $PROJECT_ROOT/cookbook/lib/recipes/scripts/install_used_gem_versions
