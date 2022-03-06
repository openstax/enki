#!/bin/bash

# Exit in case of error
set -e

[ "${TAG}" = '' ] && echo "ERROR: Remember to set TAG" && exit 1

docker build bakery/src/scripts/. -t "openstax/cops-bakery-scripts:${TAG}"
echo "Built bakery image with tag ${TAG}"
