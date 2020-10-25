#!/bin/sh

if [ ! -d 'venv' ]; then
	$PWD/setup.sh
fi
venv/bin/python3 main.py
