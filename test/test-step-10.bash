#!/bin/bash
set -e
pip install ./bakery/scr/scripts/.[test]
pytest bakery