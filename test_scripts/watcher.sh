#!/usr/bin/env bash

function update_repo() {
  sleep 1
  git add -A
  git commit -m "Testing changes" && git push --force && git reset --soft HEAD~1
}

function run_on_cluster() {
  docker run -v ~/.ssh:/root/.ssh --rm -i \
             -e WANDB_API_KEY=$WANDB_API_KEY \
             -e GIT_MAIL=$(git config user.email) \
             -e GIT_NAME=$(git config user.name) \
             -e TEST_BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD) \
             -e ON_CLUSTER=1 \
             -u root:$(id -u $USER) $(docker build -f ./Dockerfile-flow -q .)
}

clear
update_repo
run_on_cluster
