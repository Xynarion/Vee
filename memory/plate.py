"""Interaction State plate — same shape as the lab scenario inputs.

No database. Lab fixtures and assemble_interaction_state both render through here.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from settings import DEFAULT_TIMEZONE

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_CLOCK_DATE_RE = re.compile(
    r"(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{4})",
    re.IGNORECASE,
)
_ROLE_LABEL = {"user": "Founder", "assistant": "Vee"}


def parse_clock_date(when: str) -> date:
    match = _CLOCK_DATE_RE.search(when or "")
    if not match:
        raise ValueError(f"clock has no parseable date: {when!r}")
    day, month, year = int(match.group(1)), match.group(2).lower(), int(match.group(3))
    return date(year, _MONTHS[month], day)


def calendar_week(day: date) -> Tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def previous_calendar_week(day: date) -> Tuple[date, date]:
    this_monday, _ = calendar_week(day)
    last_sunday = this_monday - timedelta(days=1)
    return last_sunday - timedelta(days=6), last_sunday


def week_bounds_for_clock(when: str) -> Dict[str, Tuple[str, str]]:
    today = parse_clock_date(when)
    this_start, this_end = calendar_week(today)
    last_start, last_end = previous_calendar_week(today)
    return {
        "this_week": (this_start.isoformat(), this_end.isoformat()),
        "last_week": (last_start.isoformat(), last_end.isoformat()),
    }


def localize(moment: datetime, tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    tz = ZoneInfo(tz_name)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tz)
    return moment.astimezone(tz)


def format_clock(moment: datetime, tz_name: str = DEFAULT_TIMEZONE) -> str:
    local = localize(moment, tz_name)
    weekday = local.strftime("%A")
    month = local.strftime("%B")
    return f"{local.strftime('%H:%M')}, {weekday} {local.day} {month} {local.year}, {tz_name}"


def format_recent_conversation(turns: Sequence[Any]) -> str:
    if not turns:
        return "(none)"
    lines = []
    for turn in turns:
        role = getattr(turn, "role", "")
        text = getattr(turn, "text", "")
        label = _ROLE_LABEL.get(str(role), str(role) or "Founder")
        lines.append(f"{label}: {text}")
    return "\n".join(lines)


def _iso(moment: Optional[datetime]) -> Optional[str]:
    if moment is None:
        return None
    return moment.isoformat()


def _history_stamp(moment: datetime, tz_name: str) -> str:
    return localize(moment, tz_name).strftime("%Y-%m-%d %H:%M")


def _history_date(moment: datetime, tz_name: str) -> str:
    return localize(moment, tz_name).date().isoformat()


def _changes_suffix(changes: Optional[Mapping[str, Any]]) -> str:
    if not changes:
        return ""
    parts = []
    for key, value in changes.items():
        if value is None:
            parts.append(f"{key} → null")
        else:
            parts.append(f"{key} → {value}")
    return "; ".join(parts)


def format_item_history(events: Sequence[Any], tz_name: str = DEFAULT_TIMEZONE) -> str:
    clauses: list[str] = []
    carried: list[str] = []

    def flush_carried() -> None:
        if not carried:
            return
        clauses.append("carried " + ", ".join(carried))
        carried.clear()

    for event in events:
        kind = str(getattr(event, "kind", "") or "updated")
        at = getattr(event, "at", None) or getattr(event, "created_at", None)
        if at is None:
            continue
        if kind == "carried":
            carried.append(_history_date(at, tz_name))
            continue
        flush_carried()
        stamp = _history_stamp(at, tz_name)
        detail = _changes_suffix(getattr(event, "changes", None))
        if detail:
            clauses.append(f"{kind} {stamp} ({detail})")
        else:
            clauses.append(f"{kind} {stamp}")
    flush_carried()
    return "; ".join(clauses)


def format_progress_item(item: Any, tz_name: str = DEFAULT_TIMEZONE) -> str:
    line = f"{item.id} | {item.type} | {item.status} | {item.title}"
    due = _iso(getattr(item, "due_at", None))
    start = _iso(getattr(item, "start_at", None))
    end = _iso(getattr(item, "end_at", None))
    if due:
        line += f" | due {due}"
    if start:
        line += f" | start {start}"
    if end:
        line += f" | end {end}"
    history = getattr(item, "history", ()) or ()
    if history:
        rendered = format_item_history(history, tz_name)
        if rendered:
            line += f"\n  history: {rendered}"
    return line


def format_progress_memory(items: Sequence[Any], tz_name: str = DEFAULT_TIMEZONE) -> str:
    if not items:
        return "(none)"
    return "\n".join(format_progress_item(item, tz_name) for item in items)


def render_interaction_state(message: str, recent: str, progress: str, when: str) -> str:
    weeks = week_bounds_for_clock(when)
    this_start, this_end = weeks["this_week"]
    last_start, last_end = weeks["last_week"]
    return f"""\
------------------------
The Interaction State
------------------------
Current message:
"{message}"

Recent conversation:
{recent}

Progress Memory:
{progress}

Current date and time:
{when}

This calendar week (current week):
{this_start} → {this_end} (Monday through Sunday)

Last calendar week (previous week):
{last_start} → {last_end} (Monday through Sunday)
"""
