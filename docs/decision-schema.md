# Vee's Decision Contract

**One message → one LLM invocation → one structured Decision.**

Vee uses the assembled Interaction State to **Judge → Plan → Say**. The LLM does **not** access the database. The backend validates its Decision, executes approved tools if needed, formats the reply, and sends it through Telegram.

## 1. Decision Output Schema

```json
{
  "intent": { "kind": "brain_dump | remember | irrelevant", "summary": "…" },
  "write": { "target_ids": [], "missing": [], "conflicts": [], "duplicate_ids": [] },
  "recall": {
    "intention": "alignment | reflection | null",
    "shape": "inventory | timeline | outcome | pattern | null",
    "order": "chronological | reverse_chronological | priority | natural | null",
    "scope": { "start": null, "end": null }
  },
  "tool_calls": [],
  "response": { "type": "confirmation | clarification | testify | silence", "text": "", "show_ids": [] }
}
```

All five fields must be present. Use `null` or `[]` for inapplicable values. Unknown fields are rejected.

## 2. What each part decides

| Part | Responsibility |
|---|---|
| `intent` | Classify the message: `brain_dump`, `remember`, or `irrelevant`; summarize it briefly. |
| `write` | For brain-dumps, identify existing targets (`target_ids`), missing facts, conflicts, and duplicates. |
| `recall` | For remembering, choose the purpose, date range, presentation shape, and order. |
| `tool_calls` | Plan database actions for the backend to run in order. |
| `response` | Choose confirmation, clarification, testimony, or silence; provide text and record IDs to display. |

### Rules

**Brain-dumping**
- Match the user's changes against existing records before writing.
- If facts are missing or conflicting, leave `tool_calls` empty and ask **one short clarification question**; don't guess.
- Refer to existing records by ID (`itm_` + 16 hex characters), not by title.

**Remembering**
- `alignment` means orienting to current work; `reflection` means looking back.
- `scope.start` and `scope.end` use `YYYY-MM-DD`.
- Shapes: `inventory`, `timeline`, `outcome`, `pattern`.
- Orders: `chronological`, `reverse_chronological`, `priority`, `natural`.
- Use `response.show_ids` if the needed records are already in Interaction State. Otherwise plan `search_items` with date filters matching `recall.scope`.
- Never invent records or offer unsolicited guidance.

**Tools and replies**
- Allowed tools: `add_item`, `update_item`, `search_items` (read-only).
- `confirmation`: describe recorded changes **only after successful execution**.
- `clarification`: ask one short question.
- `testify`: give a short introduction; the backend renders only verified records from `show_ids` or search results.
- `silence`: set `response.text` to `""` for out-of-scope requests.
- The backend resolves IDs, adds execution results, applies guardrails and Bullet Journal formatting, then stores/sends the reply.

## 3. Two test cases

### A. Brain-dump

**Input:** “I finished the database setup, cancelled the webinar, moved landing page work to tomorrow, and need to send the proposal draft by Friday.”

**Expected Decision:**
- `intent.kind`: `brain_dump`
- `write.target_ids`: IDs of database setup, webinar, and landing page
- `write.missing`, `write.conflicts`, `write.duplicate_ids`: empty if unambiguous
- `recall`: empty
- `tool_calls`: three `update_item` actions and one `add_item` action
- `response.type`: `confirmation` (sent only after the backend verifies the writes)

### B. Remembering

**Input:** “What have I got today?”

**Expected Decision:**
- `intent.kind`: `remember`
- `write`: empty
- `recall`: `alignment`, `inventory`, `natural`, scope = today
- `tool_calls`: empty if today's records are already in Interaction State; otherwise `search_items`
- `response.type`: `testify`
- `response.text`: “So today, you've got:”
- `response.show_ids`: only relevant recorded items

**Backend-formatted reply (illustrative):**

```text
So today, you've got:
• Landing page
• Finalize executive summary
• Reply to Client A
○ Client meeting at 3pm
```

## 4. Data and validation reference

| Field | Allowed values |
|---|---|
| Status | `todo`, `in_progress`, `blocked`, `completed`, `dropped`, `cancelled` |
| Item type | `task`, `event` |
| Work mode | `research`, `building`, `marketing`, `personal`, or none |
| Conflict | `ambiguous_target`, `conflicting_fact` |

- Date-times must include a timezone offset (e.g. `2026-10-22T09:00:00+01:00`). A date-only deadline resolves to the end of that day.
- Infer relative dates only when unambiguous from the current time; otherwise ask for clarification.
- Reject unknown Decision fields; validate planned tool calls before execution.
- See `tools.md` for tool contracts and `voice.md` for reply style.
