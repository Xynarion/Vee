from __future__ import annotations

DEFAULT_TIMEZONE = "Europe/London"
STATE_HISTORY_WINDOW = 10
ACTIVE_STATUSES = frozenset({"todo", "in_progress"})
WORKLOAD_BUCKETS = ("today", "past", "future", "unset")  # testify / mental images later
