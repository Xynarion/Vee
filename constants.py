"""Domain invariants — shared by memory, llm, and api.

These are product/schema facts, not env knobs. Tunable defaults live in settings.py.
"""

from __future__ import annotations

import re

# --- items (matches DB enums / LLM tool args) ---

ITEM_TYPES = frozenset({"task", "event"})

ITEM_STATUSES = frozenset(
    {"todo", "in_progress", "blocked", "completed", "dropped", "cancelled"}
)

# On the plate for M3 assemble / active list queries
ACTIVE_STATUSES = frozenset({"todo", "in_progress"})

ITEM_WORK_MODES = frozenset({"research", "building", "marketing", "personal"})

# Matches memory.db.new_id("itm") → itm_ + 16 hex chars
ITEM_ID_RE = re.compile(r"^itm_[0-9a-f]{16}$")

# --- Reflect allowlist (LLM plan → app executes) ---

TOOL_NAMES = frozenset({"add_item", "update_item", "search_items"})

# --- Retrieve / testify (M6+) ---

WORKLOAD_BUCKETS = ("today", "past", "future", "unset")
