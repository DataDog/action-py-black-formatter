#!/bin/bash
set -e # Increase bash strictness
set -o pipefail

git config --global --add safe.directory /github/workspace

python /main.py
