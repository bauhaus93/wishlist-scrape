#!/bin/sh

if [ ! -d 'venv' ]; then
	python3 -mvenv venv
fi

venv/bin/pip install --upgrade pip &&
	venv/bin/pip install -r requirements.txt
