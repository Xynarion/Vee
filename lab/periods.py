"""Tally resolved periods from lab runs for debugging."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

PeriodKey = Tuple[Optional[str], Optional[str]]


def _as_period(obj: Any) -> Optional[PeriodKey]:
    if not isinstance(obj, dict):
        return None
    start, end = obj.get("start"), obj.get("end")
    if start in (None, "") and end in (None, ""):
        return None
    return (
        None if start in (None, "") else str(start),
        None if end in (None, "") else str(end),
    )


def periods_from_parsed(parsed: Any) -> Dict[str, Optional[PeriodKey]]:
    data = parsed if isinstance(parsed, dict) else {}
    understanding = ((data.get("judge") or {}) if isinstance(data.get("judge"), dict) else {}).get(
        "understanding"
    ) or {}
    testimony = ((data.get("say") or {}) if isinstance(data.get("say"), dict) else {}).get(
        "testimony"
    ) or {}
    requested = (
        understanding.get("requested_period") if isinstance(understanding, dict) else None
    )
    scope = testimony.get("scope") if isinstance(testimony, dict) else None
    return {
        "requested_period": _as_period(requested),
        "scope": _as_period(scope),
    }


def _parsed_from_run(run: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ev = run.get("evaluation") or {}
    parsed = ev.get("parsed")
    return parsed if isinstance(parsed, dict) else None


def _tally(keys: Iterable[Optional[PeriodKey]], n: int) -> List[Dict[str, Any]]:
    counts = Counter(keys)
    rows = []
    for key, count in counts.most_common():
        start, end = (None, None) if key is None else key
        rows.append(
            {
                "start": start,
                "end": end,
                "missing": key is None,
                "count": count,
                "pct": round(100.0 * count / n, 1) if n else 0.0,
            }
        )
    return rows


def stats_from_runs(runs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Count judge.requested_period and say.testimony.scope across scored runs."""
    requested: List[Optional[PeriodKey]] = []
    scopes: List[Optional[PeriodKey]] = []
    for run in runs:
        parsed = _parsed_from_run(run)
        if parsed is None:
            continue
        found = periods_from_parsed(parsed)
        requested.append(found["requested_period"])
        scopes.append(found["scope"])
    n = len(requested)
    return {
        "n": n,
        "requested_period": _tally(requested, n),
        "scope": _tally(scopes, n),
    }
