# LLM output schema

Contract for the **one** model call per turn. The model **judges**, **plans**, and **speaks** in a single JSON `Decision`. It never writes to the database or sends messages — the app validates the JSON, runs allowlisted tools, then replies.

| Role | Question | Main fields |
|---|---|---|
| **Judge** | What is going on, and are we sure? | `continuity`, `intent`, write judgments, `view`, `response.type` |
| **Plan** | What should change in memory? | `write.tool_calls` |
| **Speak** | What should the user hear? | `response.text`, `response.show_ids` |

**Rules**

- One model call per turn; model never runs SQL.
- Tools only: `add_item`, `update_item`, `search_items`.
- Uncertain → empty `tool_calls`, ask one clarification.
- Non-empty `tool_calls` → app may execute them.
- Confirmation text is a draft until the write succeeds.

---

## Shape

```json
{
  "continuity": { "summary": "…" },
  "intent": { "kind": "think | remember | irrelevant", "summary": "…" },
  "write": { },
  "view": { },
  "response": { }
}
```

| Field | Role |
|---|---|
| `continuity.summary` | How this turn relates to the open thread with the mechanism (not a replay of chat history). |
| `intent.kind` | Route: update memory / retrieve / neither. |
| `intent.summary` | One sentence: what they want this turn for progress memory. |
| `write` | Judgments + planned mutations. |
| `view` | How to retrieve when remembering. |
| `response` | What to say next. |

### Continuity

Name the discourse mode in prose (`resolve` · `continue` · `change` · `idle`).

| Mode | Meaning | Example |
|---|---|---|
| **resolve** | Answer a prior clarification | “What time?” → `"3pm"` |
| **continue** | Same thread, new content | “Also move it to Friday” |
| **change** | Subject shift | Mid-ask: “forget that — what’s on my plate?” |
| **idle** | Progress thread untouched | `"how are you"` |

Prefer: `"Resolves prior ask for family meeting time."`

### Intent

| `kind` | Meaning | Unused |
|---|---|---|
| `think` | Memory should change | `view` null |
| `remember` | Show progress back | `write` unused |
| `irrelevant` | No progress-memory work | both unused; often `silence` |

`intent.summary` examples: “Set family meeting to 3pm tomorrow.” · “See today’s open items.” · “No progress-memory ask.”

Do not confuse a **database write** with view intention **reflection** (“what happened?”).

---

## `write`

```json
{
  "operation": "add | update | complete | cancel | null",
  "target_ids": [],
  "missing": [{ "field": "start_at", "for": "family meeting", "reason": "…" }],
  "conflicts": [{
    "type": "ambiguous_target | conflicting_fact",
    "phrase": "the meeting",
    "candidate_ids": ["itm_a1b2c3d4e5f67890"],
    "reason": "…"
  }],
  "duplicate_ids": [],
  "tool_calls": []
}
```

| Field | Rules |
|---|---|
| `operation` | Coarse write intent. `complete` / `cancel` map to `update_item` + status. |
| `target_ids` | Existing item ids to touch (`itm_` + 16 hex). |
| `missing` | Facts needed before a faithful write → leave `tool_calls` empty. |
| `conflicts` | Ambiguous target or conflicting fact → leave `tool_calls` empty. |
| `duplicate_ids` | Existing ids that would duplicate an add. |
| `tool_calls` | Ordered allowlisted steps. Non-empty ⇒ app may run them. |

No write: `operation` null, `tool_calls` `[]`. Blockers explain *why* if a change seemed intended.

### Tools

**`add_item`**

```json
{
  "name": "add_item",
  "args": {
    "title": "Call the doctor",
    "type": "task",
    "parent_id": null,
    "start_at": null,
    "end_at": null,
    "due_at": null,
    "status": "todo",
    "work_mode": null
  }
}
```

**`update_item`**

```json
{
  "name": "update_item",
  "args": {
    "id": "itm_a1b2c3d4e5f67890",
    "title": "Call the doctor",
    "new_title": null,
    "status": "completed"
  }
}
```

`title` must match the current title (identity). `new_title` renames. Omit unchanged fields.

**`search_items`** — read-only lookup when Live State is not enough.

```json
{
  "name": "search_items",
  "args": {
    "query": "server invoice",
    "status": null,
    "type": null,
    "limit": 20
  }
}
```

### Enums & time

| | Values |
|---|---|
| Status | `todo` · `in_progress` · `blocked` · `completed` · `dropped` · `cancelled` |
| Type | `task` · `event` |
| `work_mode` | `research` · `building` · `marketing` · `personal` · null |

Set `start_at` / `end_at` / `due_at` only when the user stated them or they are unambiguous from the prompt clock. Otherwise null + `missing` + clarification.

---

## `view`

Filled when `intent.kind = remember`; otherwise all null.

```json
{
  "intention": "alignment | reflection | null",
  "shape": "inventory | timeline | outcome | pattern | null",
  "order": "chronological | reverse_chronological | priority | natural | null",
  "scope": { "start": "YYYY-MM-DD | null", "end": "YYYY-MM-DD | null" }
}
```

| Field | Meaning |
|---|---|
| `intention` | **alignment** — what remains; **reflection** — what happened |
| `shape` | Arrangement of the mental image |
| `order` | Sequencing within the shape |
| `scope` | Period (`start` / `end`) |

The app renders the plate; the model supplies subject + evidence ids, not a raw dump.

---

## `response`

```json
{
  "type": "confirmation | clarification | testify | silence",
  "text": "",
  "show_ids": []
}
```

| `type` | When | `text` | `show_ids` |
|---|---|---|---|
| `confirmation` | Write applied | Brief ack (draft until DB succeeds) | Optional written ids |
| `clarification` | One fact blocks a faithful write/view | One minimal question | Candidates if useful |
| `testify` | Retrieve | Short subject (or pattern claim) | Evidence ids |
| `silence` | Nothing to say | `""` | `[]` |

### Id format

`target_ids`, `duplicate_ids`, `candidate_ids`, `show_ids`, and `update_item.args.id` are DB item ids only: `itm_` + 16 lowercase hex (e.g. `itm_a1b2c3d4e5f67890`). Not titles. Use `[]` when none.

---

## By intent

| `intent.kind` | `write` | `view` | `response.type` |
|---|---|---|---|
| `think` (clear) | `tool_calls` set | null | `confirmation` |
| `think` (uncertain) | blockers, empty tools | null | `clarification` |
| `remember` | unused | filled | `testify` |
| `irrelevant` | unused | unused | `silence` |

---

## Example

```json
{
  "continuity": {
    "summary": "Idle — new brain dump; no open clarification to resolve."
  },
  "intent": {
    "kind": "think",
    "summary": "Mark landing page completed; keep pay server invoice open."
  },
  "write": {
    "operation": "update",
    "target_ids": ["itm_a1b2c3d4e5f67890"],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": [],
    "tool_calls": [
      {
        "name": "update_item",
        "args": {
          "id": "itm_a1b2c3d4e5f67890",
          "title": "Ship landing page",
          "new_title": null,
          "status": "completed"
        }
      },
      {
        "name": "add_item",
        "args": {
          "title": "Pay server invoice",
          "type": "task",
          "parent_id": null,
          "start_at": null,
          "end_at": null,
          "due_at": null,
          "status": "todo",
          "work_mode": null
        }
      }
    ]
  },
  "view": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": { "start": null, "end": null }
  },
  "response": {
    "type": "confirmation",
    "text": "Witnessed: landing page completed; pay server invoice still open.",
    "show_ids": ["itm_a1b2c3d4e5f67890"]
  }
}
```
