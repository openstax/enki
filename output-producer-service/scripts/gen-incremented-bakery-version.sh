#!/usr/bin/env bash

part_to_bump=$1

current_version=$(npm show @openstax/bakery-cli version)

read -ra major_minor_patch <<< "${current_version//./ }"

case $part_to_bump in
  major)
    ((major_minor_patch[0]++))
    major_minor_patch[1]=0
    major_minor_patch[2]=0
    ;;
  minor)
    ((major_minor_patch[1]++))
    major_minor_patch[2]=0
    ;;
  patch)
    ((major_minor_patch[2]++))
    ;;
  *)
    echo "Usage: $0 major|minor|patch" >&2
    exit 1
    ;;
esac

new_version="${major_minor_patch[0]}.${major_minor_patch[1]}.${major_minor_patch[2]}"
echo $new_version
