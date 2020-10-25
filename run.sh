#!/bin/sh

if [ ! -d 'venv' ]; then
	$PWD/setup.sh
fi
source venv/bin/activate &&
	python3 main.py
