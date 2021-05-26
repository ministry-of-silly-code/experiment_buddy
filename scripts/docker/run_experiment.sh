#! /bin/bash

set -e

. $(dirname "$0")/common.sh

GIT_URL=$1
ENTRYPOINT=$2
HASH_COMMIT=$3

load_git_folder "$GIT_URL" "$HASH_COMMIT"

docker-compose up
