#!/usr/bin/env bash
# Pilot: B01 + A01 in all 4 cells on Sonnet 5.5 = 8 trials (estimated < $0.30).
# Purpose: check the loop, transcripts and cost per trial before the full grid. Not a result.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/run_grid.sh claude-sonnet-5-5 1 1.00 results/pilot 2
