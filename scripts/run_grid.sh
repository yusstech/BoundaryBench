#!/usr/bin/env bash
# Run the 2x2 (warning on/off x channel prompt/tool_result) grid for one model.
#
# Usage: scripts/run_grid.sh MODEL REPEATS MAX_USD OUTDIR [LIMIT]
#   MAX_USD is split evenly across the 4 cells so a budget stop never leaves one cell empty.
#   LIMIT (optional) keeps only the first N scenarios (pilot: 2 = B01, A01).
#   DATA env var selects the scenario file (default data/scenarios.jsonl), e.g.
#   DATA=data/scenarios_v2_plausible.jsonl scripts/run_grid.sh ...
#
# The API key is read from macOS Keychain (service "boundarybench-anthropic") and passed only
# to the Python process environment. It is never echoed, logged or written to results.
# One-time setup, in YOUR terminal:  security add-generic-password -a "$USER" -s boundarybench-anthropic -w
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL=${1:?model}; REPEATS=${2:?repeats}; MAX_USD=${3:?max usd}; OUTDIR=${4:?outdir}; LIMIT=${5:-}
DATA=${DATA:-data/scenarios.jsonl}
[[ -f $DATA ]] || { echo "No data file $DATA"; exit 1; }
PY=.venv/bin/python
[[ -x $PY ]] || { echo "Missing .venv: python3 -m venv .venv && .venv/bin/pip install '.[live]'"; exit 1; }

if ! KEY=$(security find-generic-password -a "$USER" -s boundarybench-anthropic -w 2>/dev/null); then
  echo "No key in Keychain. Run in your terminal: security add-generic-password -a \"\$USER\" -s boundarybench-anthropic -w"
  exit 1
fi

$PY -m unittest discover -s tests >/dev/null 2>&1 || { echo "Tests failing; refusing to spend money."; exit 1; }

N_CASES=16; [[ -n $LIMIT ]] && N_CASES=$LIMIT
MAX_TRIALS=$(( N_CASES * REPEATS ))
CELL_USD=$($PY -c "print(round($MAX_USD / 4, 4))")
LIMIT_ARGS=(); [[ -n $LIMIT ]] && LIMIT_ARGS=(--limit "$LIMIT")
mkdir -p "$OUTDIR/$MODEL"

for WARNING in on off; do
  for CHANNEL in prompt tool_result; do
    CELL="$OUTDIR/$MODEL/${WARNING}_${CHANNEL}"
    if [[ -f "${CELL}_capture.json" ]]; then
      echo "== $MODEL warning=$WARNING channel=$CHANNEL already complete; skipping (delete the file to rerun)"
      continue
    fi
    echo "== $MODEL [$DATA] warning=$WARNING channel=$CHANNEL (cap \$$CELL_USD, $MAX_TRIALS trials; resumes if a checkpoint exists)"
    ANTHROPIC_API_KEY="$KEY" $PY -m boundarybench run --agent anthropic --model "$MODEL" \
      --data "$DATA" --mode instruction_only --warning "$WARNING" --channel "$CHANNEL" --effort medium \
      --repeats "$REPEATS" --max-trials "$MAX_TRIALS" --max-usd "$CELL_USD" ${LIMIT_ARGS[@]+"${LIMIT_ARGS[@]}"} \
      --out "${CELL}_capture.json" >> "${CELL}_capture.log"
    tail -n +1 "${CELL}_capture.log" | grep -E "^  [AB][0-9]" || true
    $PY -m boundarybench run --agent replay --replay-from "${CELL}_capture.json" --data "$DATA" --mode policy_gate \
      --out "${CELL}_gate.json" > /dev/null
    $PY scripts/compare.py "${CELL}_capture.json" "${CELL}_gate.json" --out "${CELL}_comparison.md" > /dev/null
  done
done
unset KEY

if grep -rqs "sk-ant" "$OUTDIR"; then echo "WARNING: key-like string found in $OUTDIR - do not share"; exit 1; fi
$PY scripts/analyze_grid.py "$OUTDIR" --out "$OUTDIR/analysis.md"
echo "Done. Read $OUTDIR/analysis.md and the *_capture.json transcripts."
