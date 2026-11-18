"""Shared lab scoring helpers. No LLM-as-judge. Never executes tools."""

from __future__ import annotations

import math
import re
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ADVICE_RE = re.compile(
    r"\b(you should|you need to|don't forget|do not forget|make sure to|"
    r"i recommend|try to|keep it up|great job|you got this|you've got this|"
    r"motivat|consider also|pro tip|remember to)\b",
    re.I,
)
SUCCESS_CLAIM_RE = re.compile(
    r"\b(saved|already (recorded|added|updated|done)|has been (added|saved|updated)|"
    r"successfully (added|updated|recorded)|i (added|updated|moved|created|saved)|"
    r"written to (the )?(database|record))\b",
    re.I,
)
_WORD_RE = re.compile(r"[a-z0-9]+")
_ITEM_ID_IN_TEXT = re.compile(r"itm_[0-9a-f]{16}", re.I)

PASS, FAIL, VARIANT, AMBER = "pass", "fail", "variant", "amber"
CLOSE_OVERALL_MIN = 90.0


def words(text: Any) -> str:
    return " ".join(_WORD_RE.findall(str(text or "").lower()))


def has_needles(text: Any, needles: Sequence[str]) -> bool:
    blob = words(text)
    return all(n in blob for n in needles)


def text_lists_records(text: Any, needles: Sequence[str]) -> List[str]:
    """Titles or item IDs that belong in say.testimony, not in the header."""
    blob = str(text or "")
    hits = [n for n in needles if n.lower() in words(blob)]
    hits.extend(_ITEM_ID_IN_TEXT.findall(blob))
    return hits


def check(
    check_id: str,
    label: str,
    status: str,
    expected: Any,
    actual: Any,
    explanation: str,
) -> Dict[str, Any]:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "expected": expected,
        "actual": actual,
        "explanation": explanation,
    }


def pct(passed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * passed / total, 2)


def mean(values: Sequence[float]) -> Optional[float]:
    return round(statistics.mean(values), 3) if values else None


def stdev(values: Sequence[float]) -> Optional[float]:
    if len(values) < 2:
        return 0.0 if len(values) == 1 else None
    return round(statistics.stdev(values), 3)


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    k = (len(ordered) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return round(ordered[lo], 3)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo), 3)


def parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def start_matches(value: Any, expected_iso: str) -> bool:
    expected = parse_dt(expected_iso)
    actual = parse_dt(value)
    return expected is not None and actual is not None and actual == expected


def fail_kind(
    *,
    strict_pass: bool,
    json_valid: bool,
    schema_valid: bool,
    raw_text: str,
    error: Optional[str],
    json_error: Optional[str],
    overall: float = 0.0,
) -> str:
    if strict_pass:
        return "pass"
    blob = f"{error or ''} {json_error or ''}".lower()
    if any(s in blob for s in ("timeout", "timed out", "exceeded")):
        return "timeout"
    if any(s in blob for s in ("connection", "connecterror", "network", "dns", "name or service")):
        return "connection"
    if "truncated" in blob or "finish_reason=" in blob:
        return "truncated"
    if not (raw_text or "").strip():
        return "empty"
    if not json_valid:
        return "invalid_json"
    if not schema_valid:
        return "schema"
    if overall >= CLOSE_OVERALL_MIN:
        return "close"
    return "scoring"


def cost_usd(
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    input_rate: float,
    output_rate: float,
) -> Optional[float]:
    if input_tokens is None and output_tokens is None:
        return None
    inp = (input_tokens or 0) / 1_000_000 * input_rate
    out = (output_tokens or 0) / 1_000_000 * output_rate
    return round(inp + out, 8)


def findings(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    evid = (data.get("judge") or {}).get("evidence") or {}
    rows = evid.get("record_findings") or []
    return rows if isinstance(rows, list) else []


def actions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    dec = (data.get("judge") or {}).get("decision") or {}
    rows = dec.get("required_actions") or []
    return rows if isinstance(rows, list) else []


def calls(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    rows = plan.get("tool_calls") or data.get("tool_calls") or []
    return rows if isinstance(rows, list) else []


def say(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = data.get("say")
    return payload if isinstance(payload, dict) else {}


def finding_for(needles: Sequence[str], rows: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for row in rows:
        blob = f"{row.get('piece_of_work', '')} {row.get('finding', '')}"
        if has_needles(blob, needles):
            return row
    return None


def eval_plan_empty(
    data: Dict[str, Any], *, why: str
) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    tool_calls = [c for c in calls(data) if isinstance(c, dict)]
    extras = tool_calls
    checks = [
        check(
            "no_tools",
            "No tool calls",
            PASS if not extras else FAIL,
            [],
            [c.get("name") for c in extras],
            why,
        ),
        check(
            "no_extra",
            "No unintended extra tool calls",
            PASS if not extras else FAIL,
            0,
            len(extras),
            "Empty plan is required." if not extras else f"Extra calls: {[c.get('name') for c in extras]}.",
        ),
    ]
    precision = 1.0 if not extras else 0.0
    recall = 1.0
    f1 = 1.0 if precision == 1.0 else 0.0
    checks.append(
        check(
            "plan_f1",
            "Plan precision / recall",
            PASS if precision == 1 and recall == 1 else FAIL,
            {"precision": 1, "recall": 1, "f1": 1},
            {"precision": precision, "recall": recall, "f1": f1, "generated": len(tool_calls)},
            "Zero tool calls is the correct plan.",
        )
    )
    return checks, precision, recall, f1, normalize_plan(tool_calls)


def normalize_plan(tool_calls: List[Dict[str, Any]]) -> List[str]:
    keys = []
    for call in tool_calls:
        name = call.get("name")
        args = call.get("args") or {}
        if name == "update_item":
            keys.append(f"update:{args.get('id')}:due={args.get('due_at')}")
        elif name == "add_item":
            keys.append(f"add:{words(args.get('title'))}:type={args.get('type')}")
        else:
            keys.append(f"{name}:{sorted(args.items())}")
    return sorted(keys)


def eval_say_hygiene(
    text: str,
    testimony: Any,
    *,
    allow_testimony: bool,
    allow_already_recorded: bool = False,
    strict_voice: bool = True,
) -> List[Dict[str, Any]]:
    coaching = bool(ADVICE_RE.search(text))
    first_person_actor = bool(re.search(r"\b(i'll|i will|i can|let me)\b", text, re.I))
    voice_ok = (not coaching) and (not first_person_actor if strict_voice else True)
    success_claim = bool(SUCCESS_CLAIM_RE.search(text))
    if allow_already_recorded and success_claim:
        only_duplicate = bool(
            re.search(r"already (recorded|added|updated|done)", text, re.I)
        ) and not bool(
            re.search(
                r"\b(saved|has been (added|saved|updated)|successfully "
                r"(added|updated|recorded)|i (added|updated|moved|created|saved)|"
                r"written to)\b",
                text,
                re.I,
            )
        )
        if only_duplicate:
            success_claim = False
    fabricated = []
    if not allow_testimony and testimony not in (None, {}):
        fabricated.append("testimony payload on a witnessing turn")
    if has_needles(text, ("priority",)) or "high priority" in words(text):
        fabricated.append("unsupported priority")
    return [
        check(
            "witness_voice",
            "Wording consistent with witness identity",
            PASS if voice_ok else FAIL,
            "No coaching, no assistant-as-actor",
            text,
            "Vee preserves the record; it does not direct work or speak as a helper doing the write.",
        ),
        check(
            "no_advice",
            "No unsolicited advice or motivation",
            PASS if not coaching else FAIL,
            "No advice",
            text,
            "Detected coaching language." if coaching else "No coaching phrases found.",
        ),
        check(
            "no_success_claim",
            "No claim that database writes already succeeded",
            PASS if not success_claim else FAIL,
            "Proposal only",
            text,
            "Confirmation is planned; tools are not executed in this lab.",
        ),
        check(
            "no_fabrication",
            "No fabricated details",
            PASS if not fabricated else FAIL,
            "No invented facts",
            fabricated or text,
            "Say must not add facts the Interaction State does not establish.",
        ),
    ]
