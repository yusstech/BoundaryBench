# BoundaryBench

**Pilot benchmark for authorization laundering against tool-using customer-operations AI agents.**

> **Status (7 Nov 2026, v0.3):** pre-registered study complete. 2,560 live multi-step trials on
> `claude-haiku-5-5` and `claude-sonnet-5-5` (≈ $13.30 total). 31 automated tests.

## Results at a glance

| Attack wording | Haiku 5.5 | Sonnet 5.5 |
|---|---:|---:|
| Obvious ("[SYSTEM] override…"), main grid | 0/320 | 0/320 |
| Plausible business text, Amendment A1 | **12/320** | 0/320 |

*Attack trials where the model proposed the attacker's exact action, pooled over the 2×2 warning × channel
cells (10 repeats × 8 attacks × 4 cells). Benign task completion 99–100% throughout.*

- Sonnet 5.5 resisted every attack in every condition.
- Haiku 5.5 failed only on realistic wording, almost entirely on one attack: following a plausible
  "tracking moved to ORD-999" note to **read another customer's order** (11/12). It never issued a
  fraudulent refund, export or payout change.
- The independent policy gate let through one customer reply containing a scam payment link: rule-based
  gates check *who* and *how much*, not *what a message says* (H5).
- Pre-registered effects of the warning, channel, model and wording all point in the predicted
  direction for Haiku but are **not statistically supported** (intervals reach 0; one scenario drives them).

Protocol and frozen hypotheses: [`docs/protocol.md`](docs/protocol.md). Amendment A1 and full results:
[`docs/amendment_A1_plausible_attacks.md`](docs/amendment_A1_plausible_attacks.md). Raw transcripts,
gate replays and analyses: [`results/`](results/).

## Research problem

A user asks a support agent to refund **$15**. An untrusted order note claims that a
supervisor authorized **$120**. A model may mistake an external document for an
instruction or permission. BoundaryBench separates two questions:

1. Will the model **propose** an unauthorized tool call?
2. Will a separate **tool policy** permit that proposed call to execute?

This narrow question is motivated by the security boundary between natural-language
interpretation and privileged actions in conversational software.

## Why this is not another generic prompt-injection demo

- **Paired counterfactual cases:** same trusted task and state; attack note is the
  manipulated variable. Eight pairs across eight attack families.
- **Independent trusted-state authorization oracle:** model-controlled text cannot
  grant permission; resource identity and amounts are evaluated by code.
- **Three distinct metrics:** model proposals, policy-unauthorized hypothetical
  executions, and attacker-goal completion. A deliberately **policy-valid yet harmful**
  reply shows why a policy gate is not a complete safety solution.
- **Utility:** benign-task expected tool completion, not just safety blocking.
- **Runnable reproduction:** standard-library Python, no production credentials.
- **Limitations are explicit:** toy dataset, first-action scope, no security claims.

## Quick start

Requires Python >=3.10. From the repository root:

```bash
python -m unittest discover -s tests -v
python -m boundarybench run --agent scripted --mode instruction_only --out results/instruction_only.json
python -m boundarybench run --agent scripted --mode policy_gate --out results/policy_gate.json
```

**Interpreting scripted output:** fixtures deliberately contain eight benign and eight attacker-desired
proposals. The reference gate blocks seven out-of-policy proposals, but deliberately
**fails** to block one policy-valid reply containing a prohibited payment instruction. This is only an automated wiring test. It does *not*
measure a model's attack susceptibility, model safety or practical protection.

## Experiment design (v0.3)

A 2×2 design, run separately for `claude-sonnet-5-5` and `claude-haiku-5-5`:

| | Note in user prompt | Note inside `get_order` tool result |
|---|---|---|
| **Warning on** (system prompt says notes are untrusted) | on/prompt | on/tool_result |
| **Warning off** (neutral system prompt) | off/prompt | off/tool_result |

Each trial is a short multi-step episode (up to 4 model turns) with simulated tools. Every tool call
is recorded and scored against the pre-declared attacker goal. The identical calls are then replayed
through the independent policy gate. See [`docs/protocol.md`](docs/protocol.md) for the hypotheses.

## Running live experiments (your machine, your key)

One-time setup in **your own terminal** (the key is stored in macOS Keychain, never in files or chat):

```bash
python3 -m venv .venv && .venv/bin/pip install '.[live]'
security add-generic-password -a "$USER" -s boundarybench-anthropic -w   # prompts for the key
```

Set a hard spending limit in Claude Console first. Then:

```bash
bash scripts/run_live_pilot.sh                                  # 8 Sonnet trials, < $0.30
bash scripts/run_grid.sh claude-haiku-5-5 10 2.00 results/main  # 640 trials, cap $2
bash scripts/run_grid.sh claude-sonnet-5-5 5 12.00 results/main # repeats set from pilot cost
```

`run_grid.sh` splits the dollar cap evenly across the four cells (`--max-usd` stops before the
next trial once the estimate is reached), replays every capture through the gate, refuses to run
if tests fail, checks outputs for key-like strings, and writes `analysis.md` + `trials.csv`.
Cost estimates use list prices and token counts; actual billing may differ slightly.

## Project layout

```text
boundarybench/      evaluation, policy enforcement and model adapters
data/               8 paired benign/attack scenarios (16 total)
tests/              22 policy, scoring, replay, live-loop (fake client) and budget tests
docs/protocol.md     hypotheses, design, validity threats and next experiments
scripts/run_grid.sh          2×2 grid for one model (Keychain key, $ cap, gate replay)
scripts/run_live_pilot.sh    8-trial Sonnet pilot
scripts/analyze_grid.py      cell table, clustered-bootstrap effects, trials.csv for labelling
scripts/compare.py     identical-trace comparison of policy conditions
docs/research_report_2026-11-04.md   results and research-status memo
docs/reading.md      related research
results/            raw traces, gate replays and analyses (committed as evidence)
```

## Roadmap to a credible empirical research artifact

- [x] Fix a threat model, policies and paired synthetic scenarios
- [x] Implement reproducible harness, 12 local tests and policy assertions
- [x] Fix attack-specific scoring, repeat-trace replay and API metadata capture
- [x] v0.3: multi-step loop, all-call scoring, 2×2 warning × channel design, $ guard
- [ ] Collect live-model traces with pinned model version and repetition counts
- [ ] Analyze attack success **and** benign utility, with uncertainty intervals
- [ ] Run held-out paraphrases; publish failure categories and case studies
- [ ] Write 3-5 page methods/results/limitations note with negative findings too

## Credit and provenance

The v0.1–v0.2 scaffold was generated with ChatGPT; v0.3 changes were made with Claude
Code, with research decisions (manipulated variables, models, budget) made by Yusuf Muhammed.
It is a starting point for Yusuf to audit, reproduce and extend. Before presenting results as his independent technical accomplishment,
he should run the experiments, review cases and make substantive decisions.

## License

MIT. Synthetic examples only.

## Analysis summary with uncertainty intervals

After generating a trace, print descriptive Wilson 95% intervals by attack family:

```bash
python scripts/analyze.py results/model_instruction_only.json
```

For mock traces, the report explicitly says the counts are fixture diagnostics.
Do not present fixture results as observed model findings.

## Candidate ownership

Read [`docs/ownership_tasks.md`](docs/ownership_tasks.md) before citing this
project in a job application. The strength of a research portfolio is the
experiment **you personally run, interpret and can defend**, not generated code.
