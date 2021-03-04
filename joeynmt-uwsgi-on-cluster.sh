#!/usr/bin/env bash
#SBATCH --job-name=joeynmt-server
#SBATCH --partition=compute
#SBATCH --nodelist=node40
#SBATCH --nodes=1
#SBATCH --mem=20GB
#SBATCH --time=1-00:00:00

THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$THIS_DIR"

PORT=5050
CLUSTER_MAIN_NODE=node00
export FLASK_APP=application:app
export FLASK_DEBUG=true

if [ -z "$CONDA_DEFAULT_ENV" ]; then
    . "$HOME"/anaconda3/etc/profile.d/conda.sh
    conda activate ma
fi

ssh -NR "$PORT":localhost:"$PORT" "$CLUSTER_MAIN_NODE" &

export JOEYNMT_SERVER_REPO="$THIS_DIR"
export JOEYNMT_SERVER_PORT="$PORT"
export FLASK_ENV=production
export ASSETS="$JOEYNMT_SERVER_REPO/assets"
mkdir -p "$ASSETS"
srun --unbuffered "$JOEYNMT_SERVER_REPO/deploy/run_uwsgi.sh"
