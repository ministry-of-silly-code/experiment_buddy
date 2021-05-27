#!/bin/bash

set -e

# Setup phase - Set the correct user.email and user.name and activate the ssh agent
eval "$(ssh-agent)" && ssh-add
git config --global user.email "$GIT_MAIL"
git config --global user.name "$GIT_NAME"

# Setup phase - Also remember to set your $WANDB_API_KEY (More info in the readme)
if [[ -z "$WANDB_API_KEY" ]]; then
  echo set \"export WANDB_API_KEY=[your-wandb-key]\" which can be found here: https://wandb.ai/settings
  exit
fi

# 1 - Create a new virtual env
virtualenv -q buddy-env  > /dev/null && source ./buddy-env/bin/activate > /dev/null

# 2 - Clone [or create] your project, in this case I'm using a basic mnist_classifier
git clone -q -b feature/testing git@github.com:DrTtnk/examples.git
cd examples

# 3 - Install the dependencies
pip install -q -e "git+https://github.com/ministry-of-silly-code/experiment_buddy.git@$BUDDY_CURRENT_TESTING_BRANCH#egg=experiment_buddy" # ToDo temporary branch for test, it will be from master when ready
pip install -q -r ./requirements.txt

# Run your experiments
python ./mnist_classifier.py
