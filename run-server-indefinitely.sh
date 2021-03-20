#!/usr/bin/env bash

THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

while true; do
    jid=$(sbatch "$THIS_DIR/joeynmt-uwsgi-on-cluster.sh" | cut -d' ' -f4)
    sleep 23h
    bash "$THIS_DIR/kill-server.sh" "$jid"
done
