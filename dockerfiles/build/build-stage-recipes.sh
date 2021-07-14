#!/bin/sh
set -e

cd $PROJECT_ROOT/recipes/
gem install bundler --no-document
gem install byebug --no-document
bundle config set no-cache 'true'
bundle config set silence_root_warning 'true'

$PROJECT_ROOT/recipes/scripts/install_used_gem_versions
