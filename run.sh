#!/bin/sh

FILE=$(realpath $0)
DIR=${FILE%/*}
$DIR/venv/bin/python3 main.py
