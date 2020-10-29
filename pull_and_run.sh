#!/bin/sh

WORK_DIR=${0%/*}
pushd $WORK_DIR
git pull --ff-only
./run.sh
popd
