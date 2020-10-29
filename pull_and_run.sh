#!/bin/sh

WORK_DIR=${0%/*}
cd $WORK_DIR
git pull --ff-only
./run.sh
