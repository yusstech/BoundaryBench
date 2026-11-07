# BoundaryBench paired tool-gate comparison

**Source:** `scripted`; gate evaluation: `replayed_scripted`.
**Evidence status:** `HARNESS_SMOKE_TEST_NOT_LLM_EVIDENCE`. If scripted, this is not a model result.

| Outcome | Without execution gate | With execution gate |
|---|---:|---:|
| Attacker goal met, sandbox only | 8/8 | 1/8 |
| Out-of-policy proposed calls | 7 | 7 |
| Out-of-policy simulated executions | 7 | 0 |
| Policy-valid malicious replies | 1 | 1 |
| Benign expected-tool execution | 100.0% | 100.0% |

## Interpretation notes

The same model proposals are scored twice, avoiding a model-sampling confound. A policy gate's efficacy on a benchmark where it is given the ground-truth authorization rules cannot establish model alignment or protection against missing rules. A completed expected-tool call is not always a semantically correct task response.
