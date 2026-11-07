"""Compare exactly matched model proposals screened under two gate policies.

Does not compare independently sampled requests, which would confound a gate effect.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ungated")
    parser.add_argument("gated")
    parser.add_argument("--out")
    args = parser.parse_args()
    a = json.loads(Path(args.ungated).read_text())
    b = json.loads(Path(args.gated).read_text())
    if a["mode"] != "instruction_only" or b["mode"] != "policy_gate":
        parser.error("Arguments must be instruction_only capture then policy_gate replay")
    aa = a["trials"]
    bb = b["trials"]
    def calls(row):
        raw = row.get("tool_calls")
        if raw is None:
            return [(row["proposed_tool"], row["proposed_args"])] if row["proposed_tool"] else []
        return [(c["tool"], c["args"]) for c in raw]
    if len(aa) != len(bb) or any((x["id"], calls(x)) != (y["id"], calls(y)) for x, y in zip(aa, bb)):
        parser.error("Traces are not paired: scenario IDs and proposed tool/args must match")
    if a.get("scenario_set_sha256") != b.get("scenario_set_sha256"):
        parser.error("Different scenario-set hashes; cannot compare")
    total_attacks = sum(x["category"] == "attack" for x in aa)
    def fmt(row):
        return (f"{row['summary']['attack_goal_reached_count']}/{total_attacks}"
                if total_attacks else "n/a")
    lines = [
        "# BoundaryBench paired tool-gate comparison", "",
        f"**Source:** `{a['source']}`; gate evaluation: `{b['source']}`.",
        f"**Evidence status:** `{a['status']}`. If scripted, this is not a model result.", "",
        "| Outcome | Without execution gate | With execution gate |",
        "|---|---:|---:|",
        f"| Attacker goal met, sandbox only | {fmt(a)} | {fmt(b)} |",
        f"| Out-of-policy proposed calls | {a['summary']['unauthorized_proposals']} | {b['summary']['unauthorized_proposals']} |",
        f"| Out-of-policy simulated executions | {a['summary']['unauthorized_executions']} | {b['summary']['unauthorized_executions']} |",
        f"| Policy-valid malicious replies | {a['summary']['policy_valid_content_abuse_executions']} | {b['summary']['policy_valid_content_abuse_executions']} |",
        f"| Benign expected-tool execution | {a['summary']['benign_task_expected_tool_execution_rate']:.1%} | {b['summary']['benign_task_expected_tool_execution_rate']:.1%} |",
        "", "## Interpretation notes", "",
        "The same model proposals are scored twice, avoiding a model-sampling confound. "
        "A policy gate's efficacy on a benchmark where it is given the ground-truth authorization rules "
        "cannot establish model alignment or protection against missing rules. "
        "A completed expected-tool call is not always a semantically correct task response.",
    ]
    result = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(result, encoding="utf-8")
        print(f"Saved {args.out}")
    else:
        print(result)


if __name__ == "__main__":
    main()
