#!/usr/bin/env bash

THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

while true; do
    jid=$(sbatch "$THIS_DIR/joeynmt-server-on-cluster.sh" | cut -d' ' -f4)
    sleep 5h
    scancel "$jid"
done

