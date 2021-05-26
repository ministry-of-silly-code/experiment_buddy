#! /bin/bash

# Script to run a single experiment

set -e

. $(dirname "$0")/common.sh

load_git_folder "$GIT_URL" "$HASH_COMMIT"

set_up_venv "buddy-venv"

log "python3 $ENTRYPOINT"
export BUDDY_IS_DEPLOYED=1

screen -m -d bash -c "python3 -O -u $ENTRYPOINT"
