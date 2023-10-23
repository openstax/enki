#!/bin/sh

if [ "$(id -u)" = "0" -a -d /data/build/data ]; then
  fix-perms -r -u app -g app /data/build/data
fi
