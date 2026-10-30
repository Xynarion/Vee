# Vee M4 — Remembering dialogue tests (manual JSON comparison)

**Goal:** Test whether Vee outputs the right **Decision JSON** over one continuous, eight-turn conversation. This tests decisions, **not** database execution or bullet formatting.

**Contract:** `decision-schema.md`.

## How to test manually

1. Give the model the system prompt, **current message**, current time, last 10 conversation messages, and the **current items** below.
2. Run the prompt once, validate its response against the Pydantic `Decision` model, then compare it with the **Expected Decision JSON**.
3. Compare the model output with the reference JSON. The examples show one acceptable wording; equivalent phrasing is fine if the decision and the chosen records match. The LLM should **not** write item bullets.
4. For the next turn, add the expected assistant reply to the recent conversation. These turns do not write, so the items stay as they are.

**Date:** Friday, 30 October 2026, Europe/London (GMT, `+00:00`). The clock starts at 16:30 and moves one minute per turn. **Tomorrow:** Saturday 31 October. **This calendar week:** Monday 26 October – Sunday 1 November.

**Item IDs:** `itm_0000000000000001` (gym), `...0002` (landing copy), `...0003` (doctor), `...0004` (family meeting), `...0005` (Hassan), `...0006` (proposal), `...0007` (standup).

**Current items:** the same seven records on every turn. Unlike the brain-dump tests, this plate includes completed and cancelled records, plus carry history, because these questions ask about them. Nothing in this dialogue changes the records.

### Comparing outputs

- **Check exactly:** `intent.kind`, `recall` (intention, shape, order, scope), `show_ids` membership, empty `write`, and empty `tool_calls`.
- **Can differ:** `intent.summary` and `response.text` wording. `show_ids` order can differ unless the turn asks for a timeline.
- `response.text` is a short introduction. The formatter renders the records behind `show_ids`. It does not invent a pattern claim; the claim in Turn 8 has to come from the model, grounded in the history on the items.

---

## Turn 1 — Day alignment

**Assembled interaction context:**

**Time:** 16:30 (30 October 2026)  
**User:** “what do i have today?”

**Recent conversation:**
```text
(none)
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Show relevant work and events for today."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "alignment",
    "shape": "inventory",
    "order": "natural",
    "scope": {
      "start": "2026-10-30",
      "end": "2026-10-30"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "Here's what's on your plate today:",
    "show_ids": [
      "itm_0000000000000002",
      "itm_0000000000000006",
      "itm_0000000000000007"
    ]
  }
}
```

**Meaning check:** Keep completed and cancelled work out of an active-work inventory. The undated open tasks can be included. At 16:30, the standup has already happened; it can appear as a today item, not as an upcoming event.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Turn 2 — Tomorrow alignment — continuity

**Assembled interaction context:**

**Time:** 16:31 (30 October 2026)  
**User:** “what about tomorrow?”

**Recent conversation:**
```text
[user] what do i have today?
[assistant] Here's what's on your plate today:
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Continue the remembering conversation and switch scope to Saturday."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "alignment",
    "shape": "inventory",
    "order": "chronological",
    "scope": {
      "start": "2026-10-31",
      "end": "2026-10-31"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "For tomorrow, you've got:",
    "show_ids": [
      "itm_0000000000000004"
    ]
  }
}
```

**Meaning check:** The family meeting on October 31 is the required item. Do not assume the October 30 standup occurs tomorrow.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Turn 3 — Day reflection

**Assembled interaction context:**

**Time:** 16:32 (30 October 2026)  
**User:** “what happened today?”

**Recent conversation:**
```text
[user] what do i have today?
[assistant] Here's what's on your plate today:
[user] what about tomorrow?
[assistant] For tomorrow, you've got:
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Summarize today’s recorded outcomes and changes."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "reflection",
    "shape": "outcome",
    "order": "chronological",
    "scope": {
      "start": "2026-10-30",
      "end": "2026-10-30"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "Here's what happened today:",
    "show_ids": [
      "itm_0000000000000001",
      "itm_0000000000000003",
      "itm_0000000000000005"
    ]
  }
}
```

**Meaning check:** Show doctor completion, Hassan meeting completion, and gym cancellation. These are *recorded* events, not independently verified facts.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Turn 4 — This-week alignment

**Assembled interaction context:**

**Time:** 16:33 (30 October 2026)  
**User:** “what's coming up this week?”

**Recent conversation:**
```text
[user] what do i have today?
[assistant] Here's what's on your plate today:
[user] what about tomorrow?
[assistant] For tomorrow, you've got:
[user] what happened today?
[assistant] Here's what happened today:
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Show upcoming work for the remainder of the current week."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "alignment",
    "shape": "timeline",
    "order": "chronological",
    "scope": {
      "start": "2026-10-30",
      "end": "2026-11-01"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "For the rest of this week, you've got:",
    "show_ids": [
      "itm_0000000000000004"
    ]
  }
}
```

**Meaning check:** The family meeting on Saturday is required. The upcoming window begins now, not on Monday; past events should not be called upcoming.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Turn 5 — Explicit timeline

**Assembled interaction context:**

**Time:** 16:34 (30 October 2026)  
**User:** “give me today's timeline”

**Recent conversation:**
```text
[user] what do i have today?
[assistant] Here's what's on your plate today:
[user] what about tomorrow?
[assistant] For tomorrow, you've got:
[user] what happened today?
[assistant] Here's what happened today:
[user] what's coming up this week?
[assistant] For the rest of this week, you've got:
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Show today’s events in time order."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "alignment",
    "shape": "timeline",
    "order": "chronological",
    "scope": {
      "start": "2026-10-30",
      "end": "2026-10-30"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "Today's recorded timeline:",
    "show_ids": [
      "itm_0000000000000007",
      "itm_0000000000000005"
    ]
  }
}
```

**Meaning check:** Team standup at 11:00 and Hassan meeting at 15:00 are both dated today. A formatter can order them using start_at. Do not include tomorrow’s family meeting.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Turn 6 — Completed this week

**Assembled interaction context:**

**Time:** 16:35 (30 October 2026)  
**User:** “what did i complete this week?”

**Recent conversation:**
```text
[user] what do i have today?
[assistant] Here's what's on your plate today:
[user] what about tomorrow?
[assistant] For tomorrow, you've got:
[user] what happened today?
[assistant] Here's what happened today:
[user] what's coming up this week?
[assistant] For the rest of this week, you've got:
[user] give me today's timeline
[assistant] Today's recorded timeline:
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Report work with a completion recorded during this week."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "reflection",
    "shape": "outcome",
    "order": "chronological",
    "scope": {
      "start": "2026-10-26",
      "end": "2026-11-01"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "This week, you completed:",
    "show_ids": [
      "itm_0000000000000003",
      "itm_0000000000000005"
    ]
  }
}
```

**Meaning check:** Only the doctor call and Hassan meeting have completed status in this fixture. Cancelled gym is not a completion.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Turn 7 — Week summary

**Assembled interaction context:**

**Time:** 16:36 (30 October 2026)  
**User:** “summarize this week”

**Recent conversation:** (last 10; the Turn 1 exchange has dropped off)
```text
[user] what about tomorrow?
[assistant] For tomorrow, you've got:
[user] what happened today?
[assistant] Here's what happened today:
[user] what's coming up this week?
[assistant] For the rest of this week, you've got:
[user] give me today's timeline
[assistant] Today's recorded timeline:
[user] what did i complete this week?
[assistant] This week, you completed:
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Give a grounded overview of this week’s completed, open, cancelled and scheduled work."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "reflection",
    "shape": "inventory",
    "order": "natural",
    "scope": {
      "start": "2026-10-26",
      "end": "2026-11-01"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "This week's recorded progress:",
    "show_ids": [
      "itm_0000000000000001",
      "itm_0000000000000002",
      "itm_0000000000000003",
      "itm_0000000000000004",
      "itm_0000000000000005",
      "itm_0000000000000006",
      "itm_0000000000000007"
    ]
  }
}
```

**Meaning check:** A full summary may include different subsets. This golden uses all seven records to show what happened and what remains. Avoid inventing a new `summary` shape.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Turn 8 — Pattern — carried work

**Assembled interaction context:**

**Time:** 16:37 (30 October 2026)  
**User:** “what kept slipping?”

**Recent conversation:** (last 10; Turns 1 and 2 have dropped off)
```text
[user] what happened today?
[assistant] Here's what happened today:
[user] what's coming up this week?
[assistant] For the rest of this week, you've got:
[user] give me today's timeline
[assistant] Today's recorded timeline:
[user] what did i complete this week?
[assistant] This week, you completed:
[user] summarize this week
[assistant] This week's recorded progress:
```

**Current items:**
```text
itm_0000000000000001 | task | cancelled | Hit the gym
  history: created 2026-10-26 09:00; carried 2026-10-27, 2026-10-28, 2026-10-29; cancelled 2026-10-30 10:00
itm_0000000000000002 | task | todo | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30
itm_0000000000000003 | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
itm_0000000000000004 | event | todo | Family meeting | start 2026-10-31 17:00
  history: created 2026-10-29 10:35; updated 2026-10-30 10:20 (start → 2026-10-31 17:00)
itm_0000000000000005 | event | completed | Meet Hassan | start 2026-10-30 15:00 | end 2026-10-30 16:00
  history: created 2026-10-29 10:40; completed 2026-10-30 16:05
itm_0000000000000006 | task | in_progress | Send proposal
  history: created 2026-10-26 10:00; carried 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30; updated 2026-10-29 14:00 (status → in_progress)
itm_0000000000000007 | event | todo | Team standup | start 2026-10-30 11:00 | end 2026-10-30 11:30
  history: created 2026-10-29 18:00
```

**Expected Decision JSON:**

```json
{
  "intent": {
    "kind": "remember",
    "summary": "Identify repeated carry-overs supported by recorded history."
  },
  "write": {
    "target_ids": [],
    "missing": [],
    "conflicts": [],
    "duplicate_ids": []
  },
  "recall": {
    "intention": "reflection",
    "shape": "pattern",
    "order": "natural",
    "scope": {
      "start": "2026-10-26",
      "end": "2026-10-30"
    }
  },
  "tool_calls": [],
  "response": {
    "type": "testify",
    "text": "The gym, landing copy and proposal kept carrying over:",
    "show_ids": [
      "itm_0000000000000001",
      "itm_0000000000000002",
      "itm_0000000000000006"
    ]
  }
}
```

**Meaning check:** The claim must be grounded in the history below. `show_ids` is the evidence; the formatter can display the records, but it cannot invent the recurrence claim.

**Next-turn state:** No write. Add this reply to the recent conversation.

## Checklist

- [ ] Turn 1: Day alignment
- [ ] Turn 2: Tomorrow alignment — continuity
- [ ] Turn 3: Day reflection
- [ ] Turn 4: This-week alignment
- [ ] Turn 5: Explicit timeline
- [ ] Turn 6: Completed this week
- [ ] Turn 7: Week summary
- [ ] Turn 8: Pattern — carried work
