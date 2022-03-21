#!/bin/sh
set -e

cd $PROJECT_ROOT/cookbook
gem install bundler --no-document
gem install byebug --no-document
bundle install 

bundle config set no-cache 'true'
bundle config set silence_root_warning 'true'