# Vee M4 — Brain-dump dialogue tests (manual JSON comparison)

**Goal:** Test whether Vee outputs the right **Decision JSON** over one continuous, eight-turn conversation. This tests decisions, **not** actual tool execution or bullet formatting.

**Contract:** `decision-schema.md`.

## How to test manually

1. Give the model the system prompt, **current message**, current time, last 10 conversation messages, and **active items**.
2. Run the prompt once, validate its response against your Pydantic `Decision` model, then compare it with the **Expected Decision JSON** below.
3. Compare the model output with the reference JSON. The examples show one acceptable wording; equivalent phrasing is fine if the decision and meaning match. The LLM should **not** write item bullets.
4. For the next turn, simulate successful tool calls and add the expected assistant response to recent conversation history. If a turn has no tools, don't change the database.

**Date:** Friday, 30 October 2026, Europe/London (GMT, `+00:00`). “Tomorrow” is 31 October 2026. Date-only task deadlines end at `23:59:59` local time.

**Item IDs:** `itm_0000000000000001` (Acme), `...0002` (gym), `...0003` (landing copy), `...0004` (login bug), `...0005` (family meeting), `...0006` (Hassan meeting). These all comply with the 16-hex-digit ID requirement.

**Initial active items:**

```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice
```

### Comparing outputs

- **Check exactly:** `intent.kind`, relevant IDs, conflict/duplicate logic, tool names and meaningful args, response type, and empty tool lists for questions/silence.
- **Can differ:** summary and reply wording, explanatory reasons, minor title wording, independent tool order, and optional `work_mode` (if valid). Keep IDs, statuses, timestamps and actual tool actions meaningful.
- `response.text` is a **proposed** introduction or plain-language note, not proof that tools have succeeded. Confirmation must be gated on actual execution by the backend.
- The full `recall` object is included each time because the schema requires it, even though these are brain-dump tests.

---
## Witness response rules and formatter handoff

- **Identity:** Vee witnesses the founder’s reported work changes and maintains a ledger. No coaching, unsolicited advice, or “Witnessed:” prefix.
- **Acknowledgement:** An optional immediate “Got it” means *received*, not *saved*. It is outside the Decision JSON.
- **LLM output:** `response.text` supplies a short introduction or clarification **without generated bullets**. `response.show_ids` selects existing records for *remembering*; for brain-dump confirmations, leave it `[]`.
- **Brain-dump confirmation:** The backend takes the successfully executed `add_item` / `update_item` results, including IDs assigned to new items, and builds the item list. It derives labels like **added**, **completed**, **cancelled**, and **moved** from the actual changes—not from LLM prose or final status alone. The Reply Formatter adds the glyphs and bullets.
- **Mixed duplicate + new write:** The LLM may use `response.text` to mention a duplicate (e.g. “Fix the login bug was already recorded.”). The formatter adds only successfully changed items, never the duplicate as a new addition.
- **Execution safety:** `response.text = "Recorded:"` is a *proposal* until writes succeed. If all fail, the formatter must not send it as a success; if some fail, it confirms only successes and reports failures. This is **not** tested in M4.
- **Clarification:** `response.text` is a single direct question; `show_ids = []`, no uncertain write calls.
- **Remembering:** Later, for `response.type = "testify"`, the LLM chooses a natural intro and existing IDs in `show_ids`; the formatter retrieves and formats actual records.
- **Silence:** `response.type = "silence"`, `response.text = ""`, `show_ids = []`, and no tool calls.

**Example formatter result (not LLM output):**

```text
Recorded:
> Acme chase — moved to tomorrow
• Hit the gym — added
• Finalize landing copy — added
• Fix the login bug — added
```

---
## Turn 1 — New work + update existing

**Assembled interaction context:**

**Time:** 10:30 (30 October 2026)  
**User:** “bump the Acme chase to tomorrow — also need to hit the gym, finalize landing copy, and fix the login bug”

**Recent conversation:**
```text
(none)
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "brain_dump",
    "summary": "Bump the Acme chase to tomorrow and add three tasks: gym, landing copy and login bug."
  },
  "write": {
    "target_ids": [
      "itm_0000000000000001"
    ],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [
    {
      "name": "update_item",
      "args": {
        "id": "itm_0000000000000001",
        "due_at": "2026-10-31T23:59:59+00:00"
      }
    },
    {
      "name": "add_item",
      "args": {
        "title": "Hit the gym",
        "type": "task",
        "work_mode": "personal"
      }
    },
    {
      "name": "add_item",
      "args": {
        "title": "Finalize landing copy",
        "type": "task",
        "work_mode": "marketing"
      }
    },
    {
      "name": "add_item",
      "args": {
        "title": "Fix the login bug",
        "type": "task",
        "work_mode": "building"
      }
    }
  ],
  "response": {
    "type": "confirmation",
    "text": "Recorded:",
    "show_ids": []
  }
}
```

**Meaning check:** Summary covers all four requests; tool calls plan one move and three additions. The LLM proposes only the introduction. After execution, the formatter lists successful changes and applies action labels and bullets.

**Next-turn state:** After successful tool execution, add gym (`2`), landing copy (`3`), login bug (`4`) to active items.

---

## Turn 2 — Event missing a time

**Assembled interaction context:**

**Time:** 10:31 (30 October 2026)  
**User:** “add family meeting today”

**Recent conversation:**
```text
[user] bump the Acme chase to tomorrow — also need to hit the gym, finalize landing copy, and fix the login bug
[assistant] Recorded:
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-10-31 23:59
itm_0000000000000002 | task | todo | Hit the gym
itm_0000000000000003 | task | todo | Finalize landing copy
itm_0000000000000004 | task | todo | Fix the login bug
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "brain_dump",
    "summary": "Add a family meeting today; the time is missing."
  },
  "write": {
    "target_ids": [],
    "missing": [
      {
        "field": "start_at",
        "for": "Family meeting",
        "reason": "An event requires a start time; only the day was provided."
      }
    ],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [],
  "response": {
    "type": "clarification",
    "text": "What time is the family meeting today?",
    "show_ids": []
  }
}
```

**Meaning check:** Summary describes adding a family meeting without a time. Missing-fact reason explains that an event start time is required. Response asks what time the family meeting is.

**Next-turn state:** No write. Keep Vee’s question in conversation history.

---

## Turn 3 — Short reply resolves the missing time

**Assembled interaction context:**

**Time:** 10:32 (30 October 2026)  
**User:** “7pm”

**Recent conversation:**
```text
[user] bump the Acme chase to tomorrow — also need to hit the gym, finalize landing copy, and fix the login bug
[assistant] Recorded:
[user] add family meeting today
[assistant] What time is the family meeting today?
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-10-31 23:59
itm_0000000000000002 | task | todo | Hit the gym
itm_0000000000000003 | task | todo | Finalize landing copy
itm_0000000000000004 | task | todo | Fix the login bug
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "brain_dump",
    "summary": "Add the family meeting today at 7pm."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [
    {
      "name": "add_item",
      "args": {
        "title": "Family meeting",
        "type": "event",
        "start_at": "2026-10-30T19:00:00+00:00",
        "work_mode": "personal"
      }
    }
  ],
  "response": {
    "type": "confirmation",
    "text": "Recorded:",
    "show_ids": []
  }
}
```

**Meaning check:** “7pm” resolves the pending family meeting; the model plans one `add_item` and proposes a brief introduction. The formatter names the new item only after the add succeeds.

**Next-turn state:** After successful execution, add family meeting (`5`) to active items.

---

## Turn 4 — New event + existing duplicate

**Assembled interaction context:**

**Time:** 10:40 (30 October 2026)  
**User:** “meet Hassan today at 3 — also add fix the login bug”

**Recent conversation:**
```text
[user] bump the Acme chase to tomorrow — also need to hit the gym, finalize landing copy, and fix the login bug
[assistant] Recorded:
[user] add family meeting today
[assistant] What time is the family meeting today?
[user] 7pm
[assistant] Recorded:
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-10-31 23:59
itm_0000000000000002 | task | todo | Hit the gym
itm_0000000000000003 | task | todo | Finalize landing copy
itm_0000000000000004 | task | todo | Fix the login bug
itm_0000000000000005 | event | todo | Family meeting | start 2026-10-30 19:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "brain_dump",
    "summary": "Add a meeting with Hassan at 3pm today; login bug is already recorded."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": [
      "itm_0000000000000004"
    ]
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [
    {
      "name": "add_item",
      "args": {
        "title": "Meet Hassan",
        "type": "event",
        "start_at": "2026-10-30T15:00:00+00:00"
      }
    }
  ],
  "response": {
    "type": "confirmation",
    "text": "Recorded. Fix the login bug was already recorded.",
    "show_ids": []
  }
}
```

**Meaning check:** Summary recognises a new Hassan meeting and the existing login-bug task. The LLM notes the duplicate in plain text; the formatter adds the new meeting only after a successful tool result.

**Next-turn state:** After successful execution, add Hassan meeting (`6`). Do not add the login bug again.

---

## Turn 5 — Ambiguous target

**Assembled interaction context:**

**Time:** 21:15 (30 October 2026)  
**User:** “done with the meeting”

**Recent conversation:**
```text
[user] bump the Acme chase to tomorrow — also need to hit the gym, finalize landing copy, and fix the login bug
[assistant] Recorded:
[user] add family meeting today
[assistant] What time is the family meeting today?
[user] 7pm
[assistant] Recorded:
[user] meet Hassan today at 3 — also add fix the login bug
[assistant] Recorded. Fix the login bug was already recorded.
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-10-31 23:59
itm_0000000000000002 | task | todo | Hit the gym
itm_0000000000000003 | task | todo | Finalize landing copy
itm_0000000000000004 | task | todo | Fix the login bug
itm_0000000000000005 | event | todo | Family meeting | start 2026-10-30 19:00
itm_0000000000000006 | event | todo | Meet Hassan | start 2026-10-30 15:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "brain_dump",
    "summary": "Mark a meeting completed, but it is unclear which meeting."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [
      {
        "type": "ambiguous_target",
        "phrase": "the meeting",
        "candidate_ids": [
          "itm_0000000000000005",
          "itm_0000000000000006"
        ],
        "reason": "Both the family meeting and the meeting with Hassan could be meant."
      }
    ],
    "duplicate_ids": []
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [],
  "response": {
    "type": "clarification",
    "text": "Which meeting did you complete — the family meeting or the meeting with Hassan?",
    "show_ids": []
  }
}
```

**Meaning check:** Summary identifies an ambiguous meeting completion. Conflict reason explains that both family and Hassan meetings fit. Clarification asks which meeting was completed.

**Next-turn state:** No write; await clarification.

---

## Turn 6 — Resolve prior question + four updates

**Assembled interaction context:**

**Time:** 21:16 (30 October 2026)  
**User:** “Hassan. Cancel the gym. The login bug is fixed. Move family meeting to tomorrow at 5pm.”

**Recent conversation:**
```text
[user] bump the Acme chase to tomorrow — also need to hit the gym, finalize landing copy, and fix the login bug
[assistant] Recorded:
[user] add family meeting today
[assistant] What time is the family meeting today?
[user] 7pm
[assistant] Recorded:
[user] meet Hassan today at 3 — also add fix the login bug
[assistant] Recorded. Fix the login bug was already recorded.
[user] done with the meeting
[assistant] Which meeting did you complete — the family meeting or the meeting with Hassan?
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-10-31 23:59
itm_0000000000000002 | task | todo | Hit the gym
itm_0000000000000003 | task | todo | Finalize landing copy
itm_0000000000000004 | task | todo | Fix the login bug
itm_0000000000000005 | event | todo | Family meeting | start 2026-10-30 19:00
itm_0000000000000006 | event | todo | Meet Hassan | start 2026-10-30 15:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "brain_dump",
    "summary": "Complete Hassan meeting and login bug, cancel gym, move family meeting to tomorrow at 5pm."
  },
  "write": {
    "target_ids": [
      "itm_0000000000000006",
      "itm_0000000000000002",
      "itm_0000000000000004",
      "itm_0000000000000005"
    ],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [
    {
      "name": "update_item",
      "args": {
        "id": "itm_0000000000000006",
        "status": "completed"
      }
    },
    {
      "name": "update_item",
      "args": {
        "id": "itm_0000000000000002",
        "status": "cancelled"
      }
    },
    {
      "name": "update_item",
      "args": {
        "id": "itm_0000000000000004",
        "status": "completed"
      }
    },
    {
      "name": "update_item",
      "args": {
        "id": "itm_0000000000000005",
        "start_at": "2026-10-31T17:00:00+00:00"
      }
    }
  ],
  "response": {
    "type": "confirmation",
    "text": "Recorded:",
    "show_ids": []
  }
}
```

**Meaning check:** Four distinct updates are planned. The LLM proposes only a short introduction. The formatter derives “completed”, “cancelled”, and “moved” from successful changes, then applies bullet formatting.

**Next-turn state:** After successful execution, only Acme (`1`), landing copy (`3`), and family meeting (`5`) remain active.

---

## Turn 7 — Contradiction with recorded time

**Assembled interaction context:**

**Time:** 21:20 (30 October 2026)  
**User:** “family meeting is at 3 tomorrow”

**Recent conversation:** (last 10; the Turn 1 exchange has dropped off)
```text
[user] add family meeting today
[assistant] What time is the family meeting today?
[user] 7pm
[assistant] Recorded:
[user] meet Hassan today at 3 — also add fix the login bug
[assistant] Recorded. Fix the login bug was already recorded.
[user] done with the meeting
[assistant] Which meeting did you complete — the family meeting or the meeting with Hassan?
[user] Hassan. Cancel the gym. The login bug is fixed. Move family meeting to tomorrow at 5pm.
[assistant] Recorded:
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-10-31 23:59
itm_0000000000000003 | task | todo | Finalize landing copy
itm_0000000000000005 | event | todo | Family meeting | start 2026-10-31 17:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "brain_dump",
    "summary": "Family meeting at 3pm tomorrow conflicts with its recorded time of 5pm."
  },
  "write": {
    "target_ids": [
      "itm_0000000000000005"
    ],
    "missing": [],
    "conflicts": [
      {
        "type": "conflicting_fact",
        "phrase": "at 3 tomorrow",
        "candidate_ids": [
          "itm_0000000000000005"
        ],
        "reason": "The family meeting is recorded for 5pm tomorrow, but the message says 3pm."
      }
    ],
    "duplicate_ids": []
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [],
  "response": {
    "type": "clarification",
    "text": "The family meeting is recorded for 5pm tomorrow. Keep 5pm or change it to 3pm?",
    "show_ids": []
  }
}
```

**Meaning check:** Summary identifies a 3pm claim conflicting with the recorded 5pm meeting. Conflict reason explains both times. Clarification asks whether to keep 5pm or change to 3pm.

**Next-turn state:** No write; retain recorded time and question.

---

## Turn 8 — Irrelevant message → silence

**Assembled interaction context:**

**Time:** 21:21 (30 October 2026)  
**User:** “how are you”

**Recent conversation:** (last 10; Turns 1 and 2 have dropped off)
```text
[user] 7pm
[assistant] Recorded:
[user] meet Hassan today at 3 — also add fix the login bug
[assistant] Recorded. Fix the login bug was already recorded.
[user] done with the meeting
[assistant] Which meeting did you complete — the family meeting or the meeting with Hassan?
[user] Hassan. Cancel the gym. The login bug is fixed. Move family meeting to tomorrow at 5pm.
[assistant] Recorded:
[user] family meeting is at 3 tomorrow
[assistant] The family meeting is recorded for 5pm tomorrow. Keep 5pm or change it to 3pm?
```

**Current items:**
```text
itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-10-31 23:59
itm_0000000000000003 | task | todo | Finalize landing copy
itm_0000000000000005 | event | todo | Family meeting | start 2026-10-31 17:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "irrelevant",
    "summary": "No progress-memory request."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": null,
    "shape": null,
    "order": null,
    "scope": {
      "start": null,
      "end": null
    }
  },
  "tool_calls": [],
  "response": {
    "type": "silence",
    "text": "",
    "show_ids": []
  }
}
```

**Meaning check:** Summary identifies that the message is unrelated to progress memory. Response must be silent: `text` stays exactly `""`.

**Next-turn state:** No tools or reply. The unresolved question from Turn 7 remains open.

---

## Separate unit tests — parser and validator

These are backend tests, not LLM dialogue turns.

| Test | Input | Expected |
|---|---|---|
| F1 | Valid JSON with tool calls | Accept |
| F2 | Valid JSON in Markdown fences | Strip fences and accept |
| F3 | Invalid JSON | Fallback; no second LLM call |
| F4 | Unknown tool name | Reject → fallback |
| F5 | Missing information and no tool calls | Accept |
| F6 | Unexpected `can_apply` field | Reject → fallback |
| F7 | Unexpected `write.operation` field | Reject → fallback |

**Note on Turn 7:** This deliberately tests “ask before overwriting” when a statement conflicts with the recorded meeting time; another product policy might treat it as an implicit correction.

**Note on statuses:** These expected outputs use `completed` and `cancelled` from the supplied dialogue fixtures. Ensure your actual tool enum uses `completed` (rather than `done`), or adjust the fixtures to match the code before testing.
