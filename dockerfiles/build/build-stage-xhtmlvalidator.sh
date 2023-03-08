#!/bin/sh
set -e

cd $PROJECT_ROOT/xhtml-validator

# Issues with gradle daemon on Apple M1 chips.
GRADLE_OPTS=-Dorg.gradle.daemon=false ./gradlew jar
