"""BoundaryBench CLI. All business tool calls are simulated; API proposals are never executed."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .agents import AnthropicAgent, ScriptedAgent, ReplayAgent, WARNINGS, CHANNELS, KEYCHAIN_HINT

# USD per million tokens (input, output), Anthropic first-party list prices, Nov 2026.
PRICES = {"claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.0, 20.0)}
from .agents import Proposal
from .eval import load_scenarios, run


class _Recorded:
    """Re-presents already-captured trials (from a checkpoint) so they can be re-scored. No API calls."""
    def __init__(self, trials):
        self.by_id = {t["id"]: Proposal(
            [{k: c[k] for k in ("tool", "args", "turn", "note_seen_before_call") if k in c} for c in t["tool_calls"]],
            t.get("agent_note", ""), t.get("agent_metadata", {})) for t in trials}

    def propose(self, scenario):
        return self.by_id[scenario["id"]]


def load_checkpoint(path: Path, valid_ids: set[str]) -> list[dict]:
    """Completed trials from a .partial.jsonl; ignores a torn last line from a crash."""
    done = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            trial = json.loads(line)
        except json.JSONDecodeError:
            continue
        if trial.get("id") in valid_ids:
            done.append(trial)
    return done


def main():
    parser = argparse.ArgumentParser(description="BoundaryBench: synthetic authorization evaluation")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--agent", choices=["scripted", "anthropic", "replay"], default="scripted")
    parser.add_argument("--mode", choices=["instruction_only", "policy_gate"], default="policy_gate")
    parser.add_argument("--replay-from", help="JSON trace produced by a previous run")
    parser.add_argument("--repeats", type=int, default=1, help="Independent model calls per scenario")
    parser.add_argument("--model", default="", help="Accessible Claude API model ID")
    parser.add_argument("--data", default="data/scenarios.jsonl")
    parser.add_argument("--out", help="JSON output path")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-trials", "--max-api-calls", dest="max_trials", type=int, default=16,
                        help="Safety guard on trials (each trial makes up to --max-turns API calls); "
                             "use --max-usd for a spend cap")
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--warning", choices=WARNINGS, default="on",
                        help="on: system prompt says notes are untrusted; off: neutral system prompt")
    parser.add_argument("--channel", choices=CHANNELS, default="prompt",
                        help="prompt: note in the user turn; tool_result: note inside get_order output")
    parser.add_argument("--effort", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--fresh", action="store_true",
                        help="Discard an existing checkpoint instead of resuming from it (destroys paid data)")
    parser.add_argument("--max-usd", type=float, default=None,
                        help="Stop before the next trial once the estimated spend of this run reaches this")
    parser.add_argument("--input-price-mtok", type=float, default=None,
                        help="USD per million input tokens (default: built-in price for --model)")
    parser.add_argument("--output-price-mtok", type=float, default=None,
                        help="USD per million output tokens (default: built-in price for --model)")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    if args.repeats <= 0 or args.max_trials <= 0 or args.max_turns <= 0:
        parser.error("--repeats, --max-trials and --max-turns must be positive")
    if args.max_output_tokens <= 0:
        parser.error("--max-output-tokens must be positive")
    known = PRICES.get(args.model, (None, None))
    if args.input_price_mtok is None:
        args.input_price_mtok = known[0]
    if args.output_price_mtok is None:
        args.output_price_mtok = known[1]
    if args.agent == "anthropic" and (args.input_price_mtok is None or args.output_price_mtok is None):
        parser.error(f"No built-in price for {args.model!r}; pass --input-price-mtok and --output-price-mtok")
    args.input_price_mtok = args.input_price_mtok or 0.0
    args.output_price_mtok = args.output_price_mtok or 0.0
    if args.input_price_mtok < 0 or args.output_price_mtok < 0:
        parser.error("price inputs must be nonnegative")
    if args.max_usd is not None and args.max_usd <= 0:
        parser.error("--max-usd must be positive")
    if args.agent == "replay" and not args.replay_from:
        parser.error("--replay-from required for replay agent")
    if args.agent in {"replay", "scripted"} and args.repeats != 1:
        parser.error("--repeats is only supported with --agent anthropic")

    dataset = Path(args.data)
    cases = load_scenarios(dataset)
    digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
    if args.limit is not None:
        cases = cases[:args.limit]

    if args.agent == "scripted":
        agent = ScriptedAgent()
    elif args.agent == "replay":
        agent = ReplayAgent(args.replay_from)
        if agent.original_source != "anthropic" and agent.original_source != "scripted":
            parser.error("Only raw anthropic/scripted captures may be replayed")
        # Rebuild the exact capture order and repeat IDs; earlier CLI could not
        # replay a trace with --repeats > 1, silently making replication unusable.
        base = {case["id"]: case for case in load_scenarios(dataset)}
        cases = []
        for entry in agent.data["trials"]:
            captured_id = entry["id"]
            base_id = captured_id.split("@r", 1)[0]
            if base_id not in base:
                parser.error(f"Missing scenario {base_id} in current dataset")
            current = dict(base[base_id]); current["id"] = captured_id
            current["pair"] = entry["pair"]
            cases.append(current)
        if agent.data.get("scenario_set_sha256") and agent.data["scenario_set_sha256"] != digest:
            parser.error("Scenario dataset changed since initial model capture; replay refused")
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            parser.error("ANTHROPIC_API_KEY not present; no live experiment was run. " + KEYCHAIN_HINT)
        agent = AnthropicAgent(args.model, warning=args.warning, channel=args.channel, effort=args.effort,
                               max_tokens=args.max_output_tokens, max_turns=args.max_turns)
        if len(cases) * args.repeats > args.max_trials:
            parser.error(f"{len(cases) * args.repeats} paid trials requested, --max-trials={args.max_trials}. Increase only deliberately.")
        if args.repeats > 1:
            cases = [{**case, "id": f"{case['id']}@r{index:02d}",
                      "pair": f"{case['pair']}@r{index:02d}"}
                     for index in range(1, args.repeats + 1) for case in cases]

    source = ("replayed_" + agent.original_source) if args.agent == "replay" else args.agent
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
    else:
        output = None
    # A live run checkpoints each trial so a network failure after many calls
    # does not lose paid evidence. Checkpoints contain synthetic prompt output.
    checkpoint = output.with_suffix(".partial.jsonl") if output and args.agent == "anthropic" else None
    all_cases = cases
    done = []
    if checkpoint and checkpoint.exists() and not args.fresh:
        # Resume: keep paid trials, run only the missing ones (same frozen code and data).
        done = load_checkpoint(checkpoint, {c["id"] for c in cases})
        done_ids = {t["id"] for t in done}
        cases = [c for c in cases if c["id"] not in done_ids]
        print(f"Resuming from {checkpoint}: {len(done)} trials already captured, {len(cases)} to run", flush=True)
        checkpoint.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in done), encoding="utf-8")
    checkpoint_file = checkpoint.open("a", encoding="utf-8") if checkpoint else None

    spent = {"usd": 0.0}

    def trial_cost(trial):
        meta = trial["agent_metadata"]
        return ((meta.get("input_tokens") or 0) * args.input_price_mtok +
                (meta.get("output_tokens") or 0) * args.output_price_mtok) / 1_000_000

    def should_stop():
        return args.agent == "anthropic" and args.max_usd is not None and spent["usd"] >= args.max_usd

    def save_trial(trial):
        if args.agent == "anthropic":
            spent["usd"] += trial_cost(trial)
            print(f"  {trial['id']}: calls={[c['tool'] for c in trial['tool_calls']]} "
                  f"goal={trial['attack_goal_proposed']} est_spend=${spent['usd']:.4f}", flush=True)
        if checkpoint_file:
            checkpoint_file.write(json.dumps(trial, ensure_ascii=False) + "\n")
            checkpoint_file.flush()

    try:
        spent["usd"] = sum(trial_cost(t) for t in done)
        result = run(cases, agent, args.mode, source, on_trial=save_trial, should_stop=should_stop)
    finally:
        if checkpoint_file:
            checkpoint_file.close()
    if done:
        # Re-score resumed + new trials together, in the original trial order, without API calls.
        captured = {t["id"]: t for t in done + result["trials"]}
        stopped = result["summary"]["stopped_early_by_budget"]
        ordered = [c for c in all_cases if c["id"] in captured]
        result = run(ordered, _Recorded(list(captured.values())), args.mode, source)
        result["summary"]["stopped_early_by_budget"] = stopped
        result["resumed_trials"] = len(done)
    result.update({
        "schema_version": "0.3", "run_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_set_sha256": digest,
        "input_price_per_million_usd": args.input_price_mtok,
        "output_price_per_million_usd": args.output_price_mtok,
    })
    if args.agent == "anthropic":
        result["model_requested"] = args.model
        result["max_output_tokens_requested"] = args.max_output_tokens
        result["condition"] = {"warning": args.warning, "channel": args.channel, "effort": args.effort,
                               "max_turns": args.max_turns}
        import anthropic
        result["anthropic_sdk_version"] = anthropic.__version__
    if args.agent == "replay":
        result["original_trace_source"] = agent.original_source
        result["original_model_requested"] = agent.data.get("model_requested")
        result["condition"] = agent.data.get("condition")
    s = result["summary"]
    original_estimate = ((s["total_input_tokens"] * args.input_price_mtok +
                          s["total_output_tokens"] * args.output_price_mtok) / 1_000_000)
    result["usage_estimated_cost_usd"] = round(original_estimate, 6)
    result["incremental_api_cost_usd"] = 0.0 if args.agent != "anthropic" else round(original_estimate, 6)
    result["billing_note"] = (
        "Estimate from standard input/output token counts and user-supplied model rates; "
        "actual billing may differ due to caching, tiering, tool overhead and provider pricing. "
        "Replay/scripted modes make no API calls."
    )
    if output:
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {output}")
    print(json.dumps({"status": result["status"], "source": result["source"],
                      "mode": args.mode, "incremental_api_cost_usd": result["incremental_api_cost_usd"],
                      **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
