#!/bin/sh

if [ "$(id -u)" = "0" -a -d /tmp/build/0000000 ]; then
  fix-perms -r -u app -g app /tmp/build/0000000
fi
