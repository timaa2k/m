#!/bin/sh

python3 -m venv test-env

source test-env/bin/activate

pip install --upgrade pip

pip install -e '.[dev]'

pyinstaller --onefile src/m/cli.py

deactivate

rm -rf test-env

mv dist/cli dist/m
