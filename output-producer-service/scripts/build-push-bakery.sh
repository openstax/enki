#!/bin/bash

# Exit in case of error
set -e

TAG=${TAG-$(date '+%Y%m%d.%H%M%S')}
TAG=${TAG} ./scripts/build-bakery.sh
docker push "openstax/cops-bakery-scripts:${TAG}"
