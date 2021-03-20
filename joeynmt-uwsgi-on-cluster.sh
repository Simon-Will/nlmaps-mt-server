#!/usr/bin/env bash
#SBATCH --job-name=joeynmt-server
#SBATCH --partition=compute
#SBATCH --nodelist=node40
#SBATCH --nodes=1
#SBATCH --mem=5GB
#SBATCH --time=1-00:00:00

PORT=5050
CLUSTER_MAIN_NODE=node00
export FLASK_APP=joeynmt_server.fullapp:app
export FLASK_ENV=production
export FLASK_DEBUG=true
export JOEYNMT_SERVER_REPO="$HOME/ma/joeynmt-server"
export JOEYNMT_SERVER_PORT="$PORT"
export ASSETS="$JOEYNMT_SERVER_REPO/assets"

if [ -z "$CONDA_DEFAULT_ENV" ]; then
    . "$HOME"/anaconda3/etc/profile.d/conda.sh
    conda activate ma
fi

ssh -NR "$PORT":localhost:"$PORT" "$CLUSTER_MAIN_NODE" &

srun --unbuffered "$JOEYNMT_SERVER_REPO/deploy/run_uwsgi.sh"
