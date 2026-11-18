"""Deterministic evaluator for lab scenarios. No LLM-as-judge. Never executes tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lab.contract import parse_json, validate_decision
from lab.scoring.brain_dump import EVALUATORS as BRAIN_DUMP_EVALUATORS
from lab.scoring.common import (
    FAIL,
    PASS,
    VARIANT,
    cost_usd,
    fail_kind,
    mean,
    pct,
    percentile,
    stdev,
)
from lab.scoring.remembering import EVALUATORS as REMEMBERING_EVALUATORS

EVALUATORS = {**BRAIN_DUMP_EVALUATORS, **REMEMBERING_EVALUATORS}
DEFAULT_EVAL_ID = "brain-dump-01"


def evaluate_decision(
    raw_text: str,
    *,
    input_rate: float,
    output_rate: float,
    usage: Optional[Dict[str, Any]] = None,
    latency: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Score one completed run. Incomplete streams must not be passed here."""
    usage = usage or {}
    latency = latency or {}
    sid = scenario_id or DEFAULT_EVAL_ID
    data, json_error = parse_json(raw_text) if raw_text else (None, error or "empty model output")
    json_valid = json_error is None and data is not None
    decision = None
    schema_errors: List[str] = []
    if json_valid:
        decision, schema_errors = validate_decision(data or {})
    schema_valid = decision is not None

    payload = data or {}
    judge_checks: List[Dict[str, Any]] = []
    plan_checks: List[Dict[str, Any]] = []
    say_checks: List[Dict[str, Any]] = []
    precision = recall = f1 = 0.0
    normalized: List[str] = []
    pack = EVALUATORS.get(sid) or EVALUATORS[DEFAULT_EVAL_ID]
    if json_valid:
        judge_fn, plan_fn, say_fn = pack
        judge_checks = judge_fn(payload)
        plan_checks, precision, recall, f1, normalized = plan_fn(payload)
        say_checks = say_fn(payload)

    def _rate(checks: List[Dict[str, Any]]) -> float:
        applicable = [c for c in checks if c["id"] != "plan_f1"]
        if not applicable:
            return 0.0
        passed = sum(1 for c in applicable if c["status"] in {PASS, VARIANT})
        return pct(passed, len(applicable))

    judgement = _rate(judge_checks) if json_valid else 0.0
    say_score = _rate(say_checks) if json_valid else 0.0
    plan_f1 = round(100.0 * f1, 2) if json_valid else 0.0
    overall = round(0.30 * judgement + 0.50 * plan_f1 + 0.20 * say_score, 2)

    critical = [c for c in judge_checks + plan_checks + say_checks if c["id"] != "plan_f1"]
    critical_ok = bool(critical) and all(c["status"] in {PASS, VARIANT} for c in critical)
    extra_ok = all(c["status"] != FAIL or c["id"] != "no_extra" for c in plan_checks)
    strict_pass = bool(
        json_valid and schema_valid and critical_ok and extra_ok and precision == 1 and recall == 1
    )

    kind = fail_kind(
        strict_pass=strict_pass,
        json_valid=json_valid,
        schema_valid=schema_valid,
        raw_text=raw_text or "",
        error=error,
        json_error=json_error,
        overall=overall,
    )
    if strict_pass:
        status = "PASS"
    elif kind == "close":
        status = "CLOSE"
    else:
        status = "FAIL"
    in_tok = usage.get("input_tokens")
    out_tok = usage.get("output_tokens")
    cost = cost_usd(in_tok, out_tok, input_rate, output_rate)
    tps = None
    total_s = latency.get("total_s")
    if out_tok is not None and total_s:
        tps = round(out_tok / total_s, 3)

    return {
        "gates": {
            "json_valid": json_valid,
            "schema_valid": schema_valid,
            "strict_pass": strict_pass,
        },
        "scores": {
            "judgement": judgement,
            "plan_precision": round(precision * 100, 2),
            "plan_recall": round(recall * 100, 2),
            "plan_f1": plan_f1,
            "say": say_score,
            "overall": overall,
        },
        "checks": {"judge": judge_checks, "plan": plan_checks, "say": say_checks},
        "fail_kind": kind,
        "json_error": json_error or error,
        "schema_errors": schema_errors,
        "parsed": payload if json_valid else None,
        "normalized_plan": normalized,
        "usage": {
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "tokens_per_sec": tps,
            "cost_usd": cost,
        },
        "latency": latency,
        "status": status,
    }


def aggregate(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    completed = [r for r in runs if r.get("evaluation")]
    n = len(completed)
    if n == 0:
        return {
            "completed": 0,
            "strict_pass_rate": 0,
            "weighted_accuracy": 0,
            "json_validity": 0,
            "schema_validity": 0,
            "judgement": 0,
            "plan_f1": 0,
            "say": 0,
            "p50_latency_s": None,
            "p95_latency_s": None,
            "mean_latency_s": None,
            "stdev_latency_s": None,
            "avg_tokens_per_sec": None,
            "total_cost_usd": None,
            "plan_consistency": None,
        }

    evs = [r["evaluation"] for r in completed]
    timed = [
        e["latency"]["total_s"]
        for e in evs
        if (e.get("latency") or {}).get("total_s") is not None
        and not (e.get("latency") or {}).get("api_error")
    ]
    tps_vals = [
        e["usage"]["tokens_per_sec"]
        for e in evs
        if (e.get("usage") or {}).get("tokens_per_sec") is not None
    ]
    costs = [
        e["usage"]["cost_usd"]
        for e in evs
        if (e.get("usage") or {}).get("cost_usd") is not None
    ]
    plans = [tuple(e.get("normalized_plan") or []) for e in evs if e["gates"]["json_valid"]]
    consistency = None
    if plans:
        top = max(plans.count(p) for p in set(plans))
        consistency = pct(top, len(plans))

    return {
        "completed": n,
        "strict_pass_rate": pct(sum(1 for e in evs if e["gates"]["strict_pass"]), n),
        "weighted_accuracy": mean([e["scores"]["overall"] for e in evs]) or 0,
        "json_validity": pct(sum(1 for e in evs if e["gates"]["json_valid"]), n),
        "schema_validity": pct(sum(1 for e in evs if e["gates"]["schema_valid"]), n),
        "judgement": mean([e["scores"]["judgement"] for e in evs]) or 0,
        "plan_f1": mean([e["scores"]["plan_f1"] for e in evs]) or 0,
        "say": mean([e["scores"]["say"] for e in evs]) or 0,
        "p50_latency_s": percentile(timed, 0.50),
        "p95_latency_s": percentile(timed, 0.95),
        "mean_latency_s": mean(timed),
        "stdev_latency_s": stdev(timed),
        "avg_tokens_per_sec": mean(tps_vals),
        "total_cost_usd": round(sum(costs), 8) if costs else None,
        "plan_consistency": consistency,
    }
