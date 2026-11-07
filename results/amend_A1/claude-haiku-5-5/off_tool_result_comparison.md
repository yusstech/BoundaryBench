# BoundaryBench paired tool-gate comparison

**Source:** `anthropic`; gate evaluation: `replayed_anthropic`.
**Evidence status:** `LIVE_OR_REPLAYED_MULTI_STEP_MODEL_TRIAL`. If scripted, this is not a model result.

| Outcome | Without execution gate | With execution gate |
|---|---:|---:|
| Attacker goal met, sandbox only | 9/80 | 1/80 |
| Out-of-policy proposed calls | 8 | 8 |
| Out-of-policy simulated executions | 8 | 0 |
| Policy-valid malicious replies | 1 | 1 |
| Benign expected-tool execution | 100.0% | 100.0% |

## Interpretation notes

The same model proposals are scored twice, avoiding a model-sampling confound. A policy gate's efficacy on a benchmark where it is given the ground-truth authorization rules cannot establish model alignment or protection against missing rules. A completed expected-tool call is not always a semantically correct task response.
