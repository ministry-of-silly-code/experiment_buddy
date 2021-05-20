#! /bin/bash
set -e

. ../common.sh

source /etc/profile
log "Refreshing modules..."
module purge
module load python/3.7

SCRIPT=$(realpath $0)
log "script realpath: $SCRIPT"
SCRIPTS_FOLDER=$(dirname $SCRIPT)
log "scripts home: $SCRIPTS_FOLDER"

log "cd $HOME/experiments/"
mkdir -p $HOME/experiments/
cd $HOME/experiments/

EXPERIMENT_FOLDER=$(mktemp -p . -d)
log "EXPERIMENT_FOLDER=$EXPERIMENT_FOLDER"

log "downloading source code from $1 to $EXPERIMENT_FOLDER"
git clone $1 $EXPERIMENT_FOLDER/
cd $EXPERIMENT_FOLDER
git checkout $3
log "pwd is now $(pwd)"

if ! source $HOME/venv/bin/activate; then
  log "Setting up venv @ $HOME/venv..."
  python3 -m virtualenv $HOME/"venv"
  source $HOME/venv/bin/activate
fi

log "Using shared venv @ $HOME/venv"

python3 -m pip install -q --upgrade pip

# sed -i '/torch.*/d' ./requirements.txt
python3 -m pip install -q -r "requirements.txt" --exists-action w -f https://download.pytorch.org/whl/torch_stable.html

export XLA_FLAGS=--xla_gpu_cuda_data_dir=/cvmfs/ai.mila.quebec/apps/x86_64/common/cuda/10.1/

# TODO: the client should send the mila_tools version to avoid issues
log "/opt/slurm/bin/sbatch $SCRIPTS_FOLDER/srun_python.sh $2"
/opt/slurm/bin/sbatch --comment "$(git log --format=%B -n 1)" $SCRIPTS_FOLDER/srun_python.sh $2
