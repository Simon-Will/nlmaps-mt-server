#!/usr/bin/env bash

THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

while true; do
    jid=$(sbatch "$THIS_DIR/joeynmt-uwsgi-on-cluster.sh" | cut -d' ' -f4)
    sleep 23h
    scancel "$jid"

    # The uwsgi must be killed with SIGINT, not SIGTERM
    # (Sending SIGINT with scancel would leave the ssh command living …)
    partition=$(scontrol show job "$jid" | sed -n 's/^ *Partition=\([^ ]\+\).*$/\1/p')
    nodelist=$(scontrol show job "$jid" | sed -n 's/^ *NodeList=\([^ ]\+\).*$/\1/p')
    srun -p "$partition" -w "$nodelist" pkill -INT -u "$USER" uwsgi
done
