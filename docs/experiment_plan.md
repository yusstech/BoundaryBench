> **Superseded (4 Nov 2026):** this describes v0.2. See `docs/protocol.md` (v0.3) and the README for the current design.

# BoundaryBench preregistration checklist, version 0.2

**This plan is not a claim that Claude was evaluated.** It describes work to be executed when the model API key is available in the researcher's local environment.

## Primary comparison

- Same model ID (`claude-sonnet-5-5` if available), tool schemas, authentication facts and system prompt for benign/attack pairs.
- Only the untrusted note is altered within each pair.
- 8 pairs, 16 unique cases, target 10 independent model samples per case (160 requests), conditional on pilot quality and API budget.
- Log each raw tool proposal in a private/local JSON trace and replay it under instruction-only execution and the same independent policy. Do not resample the model to compare gate conditions.
- Exclude none silently. Flag truncated generations separately, and record those as incomplete attempts in reporting. Preserve all trial IDs.

## Outcomes

- **Primary:** predeclared attacker objective reached / attack trials, using action + argument signatures.
- **Secondary:** out-of-policy action proposals per action proposal, out-of-policy simulated executions per attack trial, benign expected-tool simulated completion per benign trial, policy-valid content abuse, no-tool responses, and model truncations.
- Report Wilson intervals and raw counts. Do not overinterpret small family-level denominators.
- The study is descriptive. It does not support a causal claim that a gate changes the model's underlying intent or robustness.

## Requirements before scaling

1. Verify API key in local shell (never log it), account credit authorization, and workspace hard spending limit.
2. Run exactly two live cases: `B01`, `A01`, save trace, confirm token billing and model ID.
3. Manually inspect outputs and check for invalid assumptions (for example, assistant may request `get_order` as a first step; no actual tool round trips are implemented).
4. Declare any rubric/scenario changes before subsequent experiments; version the test data and rerun after changes.
5. Prepare held-out adversarial note paraphrases that are not optimized against the same model used for initial exploration.

## Current weaknesses to report

- One step only: a first `get_order` call may be necessary in reality but the harness won't follow up.
- Exact attacker-goal signatures can miss semantically equivalent deviations.
- The gate has task-specific rules and uses synthetic trusted facts; this structurally advantages it.
- Benign expected-tool completion does not check quality of natural-language replies.
- The scenario notes are obviously adversarial. Hidden prompt injection in realistic documents may behave differently.
- The benchmark does not test model scheming, frontier control failure, or actual payment infrastructure.

## Research directions if results warrant

- Compare provenance labels for a retrieved note while keeping instructions and trusted state constant.
- Add a semantic check of customer reply content and measure false positives on benign replies.
- Test with a real multi-step but synthetic environment, including `get_order` tool results.
- Measure gate-and-monitor combinations, and separate coverage gaps from model failures.
