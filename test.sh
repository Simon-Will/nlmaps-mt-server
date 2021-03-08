#!/usr/bin/env bash

NUM_TESTS="${1:-10}"
WAIT_TIME="${2:-0.2}"

THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TEST_PY="$THIS_DIR/test.py"

START_TIME=$(date +%s.%N)
for ((i=0; i<$NUM_TESTS; ++i)); do
    python "$TEST_PY" &
done | awk '{ CUM += $1; print; }
END { AVG = CUM / NR; print "CUM: " CUM "; AVG: " AVG; }'
END_TIME=$(date +%s.%N)
echo "TOTAL: $(bc -l <<<"$END_TIME - $START_TIME")"
