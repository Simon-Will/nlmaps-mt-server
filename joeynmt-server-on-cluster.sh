#!/usr/bin/env bash
#SBATCH --job-name=joeynmt-server
#SBATCH --partition=students
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --mem=5GB
#SBATCH --time=3-00:00:00

THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$THIS_DIR"

PORT=5051
CLUSTER_MAIN_NODE=node00
export FLASK_APP=joeynmt_server.fullapp:app
export FLASK_ENV=development
export FLASK_DEBUG=true
export JOEYNMT_SERVER_REPO="$HOME/ma/joeynmt-server"
export ASSETS="$JOEYNMT_SERVER_REPO/dev-assets"

if [ -z "$CONDA_DEFAULT_ENV" ]; then
    . "$HOME"/anaconda3/etc/profile.d/conda.sh
    conda activate ma
fi

ssh -NR "$PORT":localhost:"$PORT" "$CLUSTER_MAIN_NODE" &

srun --unbuffered flask run -p "$PORT"
