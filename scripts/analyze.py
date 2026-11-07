"""Small preregistered summary. Wilson intervals are descriptive, not causal proof."""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def wilson95(successes: int, n: int) -> tuple[float, float] | None:
    if n == 0:
        return None
    z = 1.95996398454
    p = successes / n
    denom = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0, mid - half), min(1, mid + half)


def report(data: dict) -> str:
    rows = data["trials"]
    groups = defaultdict(list)
    for row in rows:
        if row["category"] == "attack":
            groups[row["family"]].append(row)
    groups["ALL_ATTACKS"] = [row for row in rows if row["category"] == "attack"]
    out = [f"# BoundaryBench summary — {data['source']} / {data['mode']}",
           f"\nStatus: **{data['status']}**", "",
           "| Attack family | Goal reached | Trials | Fraction | 95% Wilson interval |",
           "|---|---:|---:|---:|---:|"]
    for name, group in sorted(groups.items()):
        hits = sum(bool(r["attack_goal_reached_in_simulation"]) for r in group)
        n = len(group)
        lo, hi = wilson95(hits, n)
        out.append(f"| {name} | {hits} | {n} | {hits/n:.1%} | [{lo:.1%}, {hi:.1%}] |")
    out += ["", "**Interpretation:** If `scripted` or `replayed_scripted`, these figures are",
            "fixture sanity checks, not observed language-model outcomes. Small sample",
            "intervals do not remove synthetic-scenario selection bias."]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result_file")
    ap.add_argument("--out")
    args = ap.parse_args()
    content = report(json.loads(Path(args.result_file).read_text(encoding="utf-8")))
    if args.out:
        Path(args.out).write_text(content, encoding="utf-8")
        print(f"saved {args.out}")
    else:
        print(content)


if __name__ == "__main__":
    main()
