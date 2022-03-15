#!/bin/bash
set -e
pipenv install ./bakery/scr/scripts/.[test]
pytest bakery