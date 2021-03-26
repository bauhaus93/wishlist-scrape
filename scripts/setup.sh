#!/bin/sh

python3 -mvenv venv && \
source venv/bin/activate && \
python3 -mpip install --upgrade pip && \
pip install -r requirements.txt 
