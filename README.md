~`mila_tools` aims to reduce the overhead to deploy experiments on mila clusters.~
@Mila users, the documentation is currently out of date,
ping me on slack @delvermm to understand how to get started.

## How to develop
Quick start

`experiment_buddy` aims to reduce the overhead to deploy experiments on servers.

buddy is a work in progress, if you are intrerested in using it in your workflow, ping me in slack @delvermm

It's important to reduce cognitive overload for the researcher measured as seconds-to-first-tensorboard datapoint

Right now it's responsabilities cover:
1. Deployment on servers
1. Handling of Sweeps
1. Tracking of hyperparameters
1. Code versioning
1. Notifications
1. Wandb integration.

Example: (Updated)

### Usage

#### Local

```shell
# 1 - Clone [or create] your project, in this case I'm using a basic mnist_classifier 
git clone https://github.com/DrTtnk/examples.git
cd examples

# 2 - Create a new virtual env
virtualenv buddy-env
source ./buddy-env/bin/activate

# 3 - Install the dependencies
pip install -q -e git+https://github.com/ministry-of-silly-code/experiment_buddy.git@feature/flow_test#egg=experiment_buddy # ToDo temporary branch for test, it will be from master
pip install -q -r ./requirements.txt

# Run your experiments
python ./mnist_classifier.py
```

#### Cluster
Same as the local one, but you have to set add to your `~/.ssh/config` the following configuration 

```shell
[INSERT MILA CONFIGURATION HERE]
```

And you need to have your cluster private key enabled, more info [here](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/adding-a-new-ssh-key-to-your-github-account) 

1. Add cluster private-key to: `https://github.com/settings/keys` if you don't know this yet, check this out [here](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/adding-a-new-ssh-key-to-your-github-account)
1. `pip install wandb && wandb init` there are two ways to set up wandb: 
    - set up wandb init from the cmd
    - or set export  WANDB_API_KEY = your wandb key which can be found here: https://wandb.ai/settings
1. `python main.py`

More details on experiment-buddy:
1. experiment-buddy will add tagged commits to a dangling branch 
2. Supports: Unix based OS

## For the tester

#### Local flow
```shell
docker run -v ~/.ssh:/root/.ssh --rm -ti \
           -e WANDB_API_KEY=$WANDB_API_KEY \
           -e GIT_MAIL=$(git config user.email) \
           -e GIT_NAME=$(git config user.name) \
           -v $(pwd)/test_scripts/test_flow.sh:/test_flow.sh ubuntu bash /test_flow.sh \
           -u root:$(id -u $USER) $(docker build -f ./Dockerfile-flow -q .)
```   

#### Remote flow
```shell
docker run -v ~/.ssh:/root/.ssh --rm -ti \
           -e WANDB_API_KEY=$WANDB_API_KEY \
           -e GIT_MAIL=$(git config user.email) \
           -e GIT_NAME=$(git config user.name) \
           -v $(pwd)/test_scripts/test_flow.sh:/test_flow.sh ubuntu bash /test_flow.sh \
           -e ON_CLUSTER=1 \
           -u root:$(id -u $USER) $(docker build -f ./Dockerfile-flow -q .)
```

#### Remote watcher
```shell
#To allow the docker to communicate with the cluster you may need to change your ~/.ssh/config permissions 
sudo chown root:$USER ~/.ssh/config && sudo chmod 640 ~/.ssh/config

#The first runs is quite slow, give it a few minutes 
nodemon --exec "./test_scripts/watcher.sh" -e py,sh
```