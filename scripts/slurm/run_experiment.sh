#! /bin/bash

set -e

. $(dirname "$0")/common.sh

GIT_URL=$1
ENTRYPOINT=$2
HASH_COMMIT=$3

load_git_folder $GIT_URL $HASH_COMMIT

source /etc/profile
log "Refreshing modules..."
module purge
module load python/3.7

set_up_venv "venv"

# sed -i '/torch.*/d' ./requirements.txt

export XLA_FLAGS=--xla_gpu_cuda_data_dir=/cvmfs/ai.mila.quebec/apps/x86_64/common/cuda/10.1/

# TODO: the client should send the mila_tools version to avoid issues
log "/opt/slurm/bin/sbatch $SCRIPTS_FOLDER/srun_python.sh $ENTRYPOINT"

/opt/slurm/bin/sbatch --comment "$(git log --format=%B -n 1)" $SCRIPTS_FOLDER/srun_python.sh $ENTRYPOINT
