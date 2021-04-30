#!/bin/sh

if [ "$(id -u)" = "0" -a -d /data/ ]; then
  fix-perms -r -u app -g app /data/
fi
