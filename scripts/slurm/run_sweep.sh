#! /bin/bash
#SBATCH --job-name=spython
#SBATCH --output=job_output.txt
#SBATCH --error=job_error.txt
#SBATCH --time=2-00:00
#SBATCH --mem=24GB
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --partition=long
#SBATCH --get-user-env=L

set -e

. $(dirname "$0")/../common.sh

GIT_URL=$1
SWEEP_ID=$2
HASH_COMMIT=$3

source /etc/profile
log "Refreshing modules..."
module purge
module load python/3.7
module load pytorch/1.7

FOLDER=$SLURM_TMPDIR/src/

pull_experiment $GIT_URL $HASH_COMMIT $FOLDER

# Set up virtualenv in $SLURM_TMPDIR. Will get blown up at job end.
log "Setting up venv @ $SLURM_TMPDIR/venv..."

python3 -m virtualenv --system-site-packages "$SLURM_TMPDIR/venv"
# shellcheck disable=SC1090
source "$SLURM_TMPDIR/venv/bin/activate"
python3 -m pip -q  install --upgrade pip

log "Downloading modules"
python3 -m pip -q  install -r "requirements.txt" --exists-action w -f https://download.pytorch.org/whl/torch_stable.html

export XLA_FLAGS=--xla_gpu_cuda_data_dir=/cvmfs/ai.mila.quebec/apps/x86_64/common/cuda/10.1/
# TODO: the client should send the experiment_buddy version to avoid issues
wandb agent "$SWEEP_ID"
