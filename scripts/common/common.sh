#! /bin/bash

set -e

# Module system
function log() {
    echo -e "\e[32m\"[DEPLOY LOG] $*\"\e[0m"
}

function pull_experiment() {
  GIT_URL=$1
  HASH_COMMIT=$2
  FOLDER=$3
  log "downloading source code from $GIT_URL to $FOLDER"
  git clone -q "$GIT_URL" "$FOLDER"/
  cd "$FOLDER" || exit
  git checkout "$HASH_COMMIT"
  log "pwd is now $(pwd)"
}

function load_git_folder() {
  SCRIPT=$(realpath $0)
  GIT_URL=$1
  HASH_COMMIT=$2

  log "script realpath: $SCRIPT"
  SCRIPTS_FOLDER=$(dirname "$SCRIPT")
  log "scripts home: $SCRIPTS_FOLDER"

  log "cd $HOME/experiments/"
  mkdir -p "$HOME"/experiments/
  cd "$HOME"/experiments/

  EXPERIMENT_FOLDER=$(mktemp -p . -d)
  pull_experiment $GIT_URL $HASH_COMMIT $EXPERIMENT_FOLDER
}

function set_up_venv() {
  VENV_NAME=$1

  [ ! -d /tmp/"$VENV_NAME" ] && python3 -m virtualenv /tmp/"$VENV_NAME" > /dev/null

  source /tmp/"$VENV_NAME"/bin/activate > /dev/null

  python3 -m pip -q install --upgrade pip

  python3 -m pip -q install -r "requirements.txt" --exists-action w
}
