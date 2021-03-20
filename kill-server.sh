#!/usr/bin/env bash

JOB_ID="$1"

if [ -z "$JOB_ID" ]; then
    echo 'Usage: kill-server.sh SLURM_JOB_ID' >&2
    exit 1
fi

PARTITION=$(scontrol show job "$JOB_ID" | sed -n 's/^ *Partition=\([^ ]\+\).*$/\1/p')
NODELIST=$(scontrol show job "$JOB_ID" | sed -n 's/^ *NodeList=\([^ ]\+\).*$/\1/p')

echo 'Terminating ssh tunnel'
scancel "$JOB_ID"

# The uwsgi must be killed with SIGINT, not SIGTERM
# (Sending SIGINT with scancel above would leave the ssh command living …)
echo 'Terminating uwsgi'
srun -Q -p "$PARTITION" -w "$NODELIST" pkill -INT -u "$USER" uwsgi

echo 'Showing remaining processes with ps ux:'
srun -Q -p "$PARTITION" -w "$NODELIST" ps ux
