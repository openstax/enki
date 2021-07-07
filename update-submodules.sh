#!/bin/bash

[[ $1 ]] && REMOTE='--remote'
[[ $1 ]] || echo -e 'Tip: Pass any argument (like "1") to this script and it will upgrade the submodules to be the latest main branch versions' && sleep 10

git submodule init
git submodule update $REMOTE