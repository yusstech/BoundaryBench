"""Analyse a 2x2 grid run: OUTDIR/<model>/<warning>_<channel>_{capture,gate}.json.

Primary outcome = attacker goal PROPOSED by the model (model behaviour, independent of any gate).
Gate outcomes come from replaying the identical calls. Descriptive only; 8 attack scenarios means
scenario-level selection dominates uncertainty, so effects use a scenario-clustered bootstrap.
"""
import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyze import wilson95  # noqa: E402

CELLS = [("on", "prompt"), ("on", "tool_result"), ("off", "prompt"), ("off", "tool_result")]


def load(outdir: Path):
    data = {}
    for model_dir in sorted(p for p in outdir.iterdir() if p.is_dir()):
        for warning, channel in CELLS:
            cap = model_dir / f"{warning}_{channel}_capture.json"
            gate = model_dir / f"{warning}_{channel}_gate.json"
            if cap.exists() and gate.exists():
                data[(model_dir.name, warning, channel)] = (
                    json.loads(cap.read_text()), json.loads(gate.read_text()))
    return data


def base_id(trial_id: str) -> str:
    return trial_id.split("@r", 1)[0]


def fmt_rate(hits: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson95(hits, n)
    return f"{hits}/{n} ({hits / n:.0%}, CI {lo:.0%}–{hi:.0%})"


def rate(rows, key):
    return sum(bool(r[key]) for r in rows) / len(rows) if rows else float("nan")


def cluster_bootstrap(attack_rows, contrast, iters=4000, seed=7):
    """Resample attack scenarios (clusters) with replacement; return point estimate and 95% interval."""
    by_scn = defaultdict(list)
    for r in attack_rows:
        by_scn[base_id(r["id"])].append(r)
    ids = sorted(by_scn)
    point = contrast(attack_rows)
    rng = random.Random(seed)
    stats = []
    for _ in range(iters):
        sample = [r for i in (rng.choice(ids) for _ in ids) for r in by_scn[i]]
        value = contrast(sample)
        if value == value:  # skip NaN
            stats.append(value)
    stats.sort()
    if not stats:
        return point, float("nan"), float("nan")
    return point, stats[int(0.025 * len(stats))], stats[int(0.975 * len(stats)) - 1]


def contrast_fn(kind):
    def cell_rate(rows, w=None, c=None):
        sub = [r for r in rows if (w is None or r["_w"] == w) and (c is None or r["_c"] == c)]
        return rate(sub, "attack_goal_proposed")

    if kind == "warning":   # off minus on, pooled over channel
        return lambda rows: cell_rate(rows, w="off") - cell_rate(rows, w="on")
    if kind == "channel":   # tool_result minus prompt, pooled over warning
        return lambda rows: cell_rate(rows, c="tool_result") - cell_rate(rows, c="prompt")
    # interaction: warning effect in tool channel minus warning effect in prompt channel
    return lambda rows: ((cell_rate(rows, "off", "tool_result") - cell_rate(rows, "on", "tool_result")) -
                         (cell_rate(rows, "off", "prompt") - cell_rate(rows, "on", "prompt")))


def report(data) -> tuple[str, list[dict]]:
    out = ["# BoundaryBench 2×2 grid analysis", "",
           "Primary outcome: **attacker goal proposed** by the model (any call matching the pre-declared",
           "signature), before any gate. `Gate` = same calls replayed through the policy gate.", ""]
    csv_rows = []
    models = sorted({k[0] for k in data})
    for model in models:
        out += [f"## {model}", "",
                "| Warning | Channel | Goal proposed (attacks) | Goal after gate | Unsafe proposal (attacks) "
                "| Benign completed & permitted | Refusals | Note seen | Turn-limit hits | Est. $ |",
                "|---|---|---|---|---|---|---:|---:|---:|---:|"]
        pooled = []
        for warning, channel in CELLS:
            if (model, warning, channel) not in data:
                continue
            cap, gate = data[(model, warning, channel)]
            atk = [t for t in cap["trials"] if t["category"] == "attack"]
            ben = [t for t in cap["trials"] if t["category"] == "benign"]
            gatk = [t for t in gate["trials"] if t["category"] == "attack"]
            s = cap["summary"]
            stopped = " ⚠️budget stop" if s.get("stopped_early_by_budget") else ""
            out.append(
                f"| {warning} | {channel}{stopped} | {fmt_rate(sum(t['attack_goal_proposed'] for t in atk), len(atk))} "
                f"| {fmt_rate(sum(t['attack_goal_reached_in_simulation'] for t in gatk), len(gatk))} "
                f"| {fmt_rate(sum(t['unsafe_proposal'] for t in atk), len(atk))} "
                f"| {fmt_rate(sum(t['expected_tool_permitted'] for t in ben), len(ben))} "
                f"| {s['refusals']} | {s['note_exposed_trials']}/{s['n_scenarios']} | {s['hit_turn_limit']} "
                f"| {cap.get('usage_estimated_cost_usd', 0):.3f} |")
            for t in cap["trials"]:
                pooled.append({**t, "_w": warning, "_c": channel})
                texts = [b.get("text", "") for turn in t["agent_metadata"].get("transcript", [])
                         for b in turn["content"] if b.get("type") == "text"]
                csv_rows.append({
                    "model": model, "warning": warning, "channel": channel, "id": t["id"],
                    "family": t["family"], "category": t["category"],
                    "calls": json.dumps([[c["tool"], c["args"]] for c in t["tool_calls"]]),
                    "goal_proposed": t["attack_goal_proposed"], "unsafe_proposal": t["unsafe_proposal"],
                    "benign_ok": t["expected_tool_permitted"], "refusal": t["refusal"],
                    "final_text": " | ".join(texts)[:400], "your_label": "", "your_notes": ""})
        attacks = [r for r in pooled if r["category"] == "attack"]
        if {(r["_w"], r["_c"]) for r in attacks} == set(CELLS):
            out += ["", "**Effects on goal-proposed rate** (scenario-clustered bootstrap, 95%):", ""]
            for kind, label in [("warning", "Warning removed (off − on)"),
                                ("channel", "Tool-result channel (tool − prompt)"),
                                ("interaction", "Interaction (warning effect in tool − in prompt)")]:
                point, lo, hi = cluster_bootstrap(attacks, contrast_fn(kind))
                out.append(f"- {label}: **{point:+.1%}** [{lo:+.1%}, {hi:+.1%}]")
        out += ["", "**Per attack family — goal proposed, by cell:**", "",
                "| Family | " + " | ".join(f"{w}/{c}" for w, c in CELLS) + " |",
                "|---|" + "---:|" * len(CELLS)]
        for family in sorted({r["family"] for r in attacks}):
            cells = []
            for w, c in CELLS:
                rows = [r for r in attacks if r["family"] == family and r["_w"] == w and r["_c"] == c]
                cells.append(f"{sum(r['attack_goal_proposed'] for r in rows)}/{len(rows)}" if rows else "–")
            out.append(f"| {family} | " + " | ".join(cells) + " |")
        out.append("")
    models_rows = defaultdict(list)
    for (model, warning, channel), (cap, _) in data.items():
        for t in cap["trials"]:
            if t["category"] == "attack":
                models_rows[model].append({**t, "_m": model})
    if len(models_rows) == 2:
        (m_a, rows_a), (m_b, rows_b) = sorted(models_rows.items())  # alphabetical: haiku, sonnet
        diff = lambda rows: (rate([r for r in rows if r["_m"] == m_a], "attack_goal_proposed") -
                             rate([r for r in rows if r["_m"] == m_b], "attack_goal_proposed"))
        point, lo, hi = cluster_bootstrap(rows_a + rows_b, diff)
        out += [f"## Model comparison (H4)", "",
                f"- {m_a} − {m_b}, goal proposed, pooled over cells: **{point:+.1%}** [{lo:+.1%}, {hi:+.1%}]", ""]
    out += ["## Reading notes", "",
            "- With 8 attack scenarios, intervals are wide; per-family cells are case studies, not estimates.",
            "- Capture assumes every simulated call succeeds; behaviour after a live gate denial is not observed.",
            "- `trials.csv` has empty `your_label` / `your_notes` columns for manual failure labelling."]
    return "\n".join(out) + "\n", csv_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--out")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    data = load(outdir)
    if not data:
        sys.exit(f"No capture/gate pairs under {outdir}")
    text, rows = report(data)
    with open(outdir / "trials.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"saved {args.out} and {outdir / 'trials.csv'}")
    else:
        print(text)


if __name__ == "__main__":
    main()
