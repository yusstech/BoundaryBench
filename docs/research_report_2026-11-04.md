> **Superseded (4 Nov 2026):** this describes v0.2. See `docs/protocol.md` (v0.3) and the README for the current design.

# BoundaryBench: An authorization-laundering evaluation of customer-operations agents

**Progress memo — 4 November 2026**  
**Evidence status: harness validation ONLY. No live Claude API experiment was executed in this environment.**  
Yusuf Muhammed. Prepared with AI assistance; see the README's *Authorship and AI assistance* section.

## Abstract

This project tests whether an AI assistant carrying out an authenticated customer request will mistakenly promote untrusted retrieved notes into instructions or authorization for privileged tool calls. The evaluation separates model action *proposals* from downstream *execution policy*, because a model can propose unsafe actions while a deterministic tool gate prevents them. Conversely, a tool gate may allow malicious content inside an otherwise authorized customer reply. We implemented eight paired benign/attack tasks and a synthetic authorization oracle and exercised the harness with predetermined fixture tool proposals. The 12 automated checks passed. **These observations concern harness behavior only, not the behavior or security of any deployed language model.** A controlled Claude pilot still requires the API key to be supplied privately in the user's own execution environment.

## Research question and contribution scope

**Question:** Does attacker-controlled text in retrieved order notes cause a tool-using AI agent to propose out-of-scope actions, and how does independent authorization change which proposed actions would execute?

The current artifact contributes a small, explicitly specified educational testbed. It is **not** a new frontier-model safety result, a production security audit, or an independently validated novel benchmark.

### Threat model

An adversary can replace one retrieved order note. It cannot modify the authenticated user's request, server-side customer/order identifiers, verified refund maximum, system prompt, tool definitions, or policy code. All records and tool operations are synthetic. The most privileged actions (refund, export, payout change) are simulated and never executed.

### Study design

There are eight matched pairs (16 scenarios total), each consisting of a benign note and an attacker-controlled note under identical trusted state and user task. The attacker goals include forged supervisor approval, refund cap inflation, bulk export instructions, cross-account lookup, payout redirection, role spoofing, unauthorized refund, and content-level manipulation of a customer reply. Tool proposals are scored against the same gate under two replayed configurations: `instruction_only` and `policy_gate`. The target for each attacker goal is pre-specified as an exact tool name and tool arguments or an explicitly identified malicious string, reducing accidental overcounting.

### Outcomes and limitations

Primary: attack-specific simulated objective completion among adversarial scenarios, expressed as numerator / attack trials. Secondary: out-of-policy model proposals, simulated out-of-policy executions, policy-valid malicious reply proposals, and benign expected-tool executions. Captured live runs also record model ID, response metadata, reported token usage, and truncated responses. A completed expected-tool call is **not** a comprehensive semantic assessment of task completion.

An appropriate live evaluation will collect 10 independent calls per scenario, maintain paired baseline/attack tasks, replay captured model outputs through an independent policy gate, and report uncertainty intervals for descriptive rates. The benchmark is small and hand-authored, tests only first actions, exposes overt attacks, and lacks long-horizon workflows or realistic application interfaces. Exploratory follow-ups should use held-out paraphrases and varying provenance before inferring generalization.

## What was executed locally

1. Code and benchmark review, including an audit of goal-specific scoring and replay behavior.
2. Twelve automated unit and integrity tests (all passing).
3. Two **scripted fixture** runs over all 16 scenarios, once with `instruction_only`, once with `policy_gate`.
4. A policy-gate replay of the *same* scripted fixture proposals.
5. A check for the Claude API environment variable, which is absent in this runtime. The live runner correctly refused to send a request. **Claude calls made: 0. API charges from this work: $0.**

### Scripted diagnostic outcomes (not model findings)

| Measure | No execution gate | Independent gate |
|---|---:|---:|
| Fixture action proposals | 16 | 16 |
| Out-of-policy action proposals | 7 | 7 |
| Out-of-policy simulated executions | 7 | 0 |
| Attacker objectives achieved | 8 of 8 | 1 of 8 |
| Benign expected-tool simulated executions | 8 of 8 | 8 of 8 |

The scenario with the residual attacker success is `A08`: `reply_to_customer` is correctly scoped to the authenticated customer and therefore permitted, but the message contains a malicious payment instruction. This is a purposeful **policy-coverage gap**, not an empirical Claude error. The seven denied fixture actions are directly encoded by the policy and prove neither model reliability nor broader protection.

## Important corrections introduced in v0.2

1. **Attack-specific measurement.** Earlier scoring treated almost any unauthorized action as achieving the attacker's goal. New scoring requires the predeclared attack tool/argument signature. Generic policy violations are tallied separately.
2. **Repeated-trial replay.** Earlier replay could not correctly reconstruct IDs such as `A01@r01`. Replays now preserve captured scenario and repeat identifiers; dataset hash mismatches are refused.
3. **Live-result traceability.** Claude proposals now include model response IDs, token counts, stop reason, and the response content from wholly synthetic tasks. Checkpoints are written after each paid call to minimize lost work on network errors.
4. **Budget controls.** The live CLI requires explicit opt-in for more than 16 requests per run and records estimated token costs. It does **not** replace a hard spending limit configured in Claude Console.
5. **Additional automated checks.** Six integrity tests were added beyond the original six policy and harness tests.

## Research context

This question is related to Anthropic's publicly described research on adversarial robustness, safeguards, and AI control. However, existing work already investigates prompt injection and authorization confusion; see Anthropic's *SLEIGHT-Bench: Finding Blind Spots in AI Monitors* (2026) and *Mitigating the risk of prompt injections in browser use* (2025). The scope here is intentionally much narrower: a synthetic customer-operations tool gate rather than general agent sabotage or a frontier monitor evaluation.

References:

- https://alignment.anthropic.com/2026/anthropic-residency/
- https://alignment.anthropic.com/2026/sleight-bench/
- https://www.anthropic.com/research/prompt-injection-defenses
- https://platform.claude.com/docs/en/models/overview

## Next experiment: controlled Claude pilot

Run `bash scripts/run_live_pilot.sh` on a machine that securely holds an API key with permission to use the promotional credits. The script initiates exactly **two paid requests** (`B01` and `A01`) to `claude-sonnet-5-5`, records raw synthetic responses and token usage, and replays them through the policy gate with no further Claude call. Inspect the trial-level data, especially text-only responses, `stop_reason=max_tokens`, unexpected tool arguments, and attack-specific goal matching. The resulting two requests are a connectivity and measurement pilot, **not** a meaningful statistical sample.

If the pilot succeeds, preregister any changes, run the remaining 14 cases, and then collect repeated samples. Document the actual model ID returned by the API and estimate spending using the reported token counts. Avoid comparing separate model draws to measure the gate's effect; replay the identical proposals. Do not claim data which has not been observed.

## Contribution statement

See the README's *Authorship and AI assistance* section for the current statement.
