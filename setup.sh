#!/bin/sh

if [ ! -d 'venv' ]; then
	python3 -mvenv venv
fi

source venv/bin/activate &&
	pip install --upgrade pip &&
	pip install -r requirements.txt
