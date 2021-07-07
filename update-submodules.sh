#!/bin/bash

[[ $SKIP_SUBMODULE_UPGRADE ]] || REMOTE='--remote'

git submodule init
git submodule update $REMOTE