#!/bin/bash
set -e

echo "WARN: Book Disassembly hangs without making a tweak. Comment a few lines and try again. See https://github.com/openstax/output-producer-service/pull/372"
sleep 10

# Draw the dependency graph PNG files
(cd ./build-concourse/ && npm install && npm run draw-graphs)
