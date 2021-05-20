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
  git clone "$GIT_URL" "$FOLDER"/
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

set_up_venv() {
  VENV_NAME=$1
  if ! source $HOME/"$VENV_NAME"/bin/activate; then
    log "Setting up venv @ $HOME/$VENV_NAME..."
    python3 -m virtualenv "$HOME"/"$VENV_NAME"
    source "$HOME"/"$VENV_NAME"/bin/activate
  fi

  log "Using shared venv @ $HOME/$VENV_NAME"

  python3 -m pip -q  install --upgrade pip

  python3 -m pip -q install -r "requirements.txt" --exists-action w -f https://download.pytorch.org/whl/torch_stable.html
}
