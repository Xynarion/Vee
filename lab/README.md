# Vee Decision Lab

Local benchmark dashboard for **one Together call per run**. Two fixture packs share the dropdown:

- **Brain-dump** Scenarios 01–07 (new work, missing event time, time resolved, duplicate login, four updates, conflicting family-meeting time, silence on a greeting).
- **Remembering** Scenario 01 (day alignment: `what do i have today?` on Saturday 14 November 2026) and Scenario 02 (last-week reflection: `What did I get done last week?` on Saturday 14 November 2026). Each has its own Progress Memory plate. Last week is Monday 2 November through Sunday 8 November 2026: completed pricing, coffee, expenses, and weekly review. Traps include cancelled gym, uncompleted standup, prior-week doctor, this-week invoice/proposal/flights, open landing copy, and today's family meeting. Interaction State includes this calendar week and last calendar week, derived from the clock.

Planned `add_item` / `update_item` / `search_items` calls are **scored as data and never executed**. The default scenario is Remembering / Scenario 02. A run is **PASS** only if every check is pass/variant. Schema-valid runs at **90%+** overall that miss a check are **CLOSE**, not FAIL.

Portable: Python + FastAPI + SQLite + one HTML file. No Node, no Postgres.

## Contract notes (not silent prompt edits)

The model is sent `llm/prompt.py` unchanged.

- The prompt’s output object is `judge` / `plan` / `say`. That is `llm.schema.Decision`; the lab validates the same contract.
- The prompt’s example JSON is instructional notation, not literal JSON Schema, and has a stray `}` inside `plan.tool_calls`. The lab validates the intended object, not that typo.
- If `say.types` includes `testimony`, `say.testimony` is required. A null payload is a schema failure, not a pass.
- `say.testimony.aim`, `view_reason`, and `scope_reason` are required. `purpose_reason` is still required: why orientation or reflection. The scope reason should name the current date and why those start/end dates were chosen.
- Remembering scores temporal reasoning in three independent places: `judge.understanding.requested_period` (clock resolution), `say.testimony.scope` (presented window), and `item_ids` (records for the correctly resolved period). A wrong week fails those checks even when the selected IDs match Vee's incorrect window.
- `json_object` is the default Together response format. `json_schema` is an optional experiment setting and may not be supported by Qwen3.5-9B.

## Setup

```bash
cd company-progress-memory-mechanism
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set TOGETHER_API_KEY for live runs
```

## Launch

```bash
docker compose up -d
# lab only, on the host: python -m lab
# Do not use --reload: open SSE streams deadlock the reloader when prompt.py changes.
```

Open http://127.0.0.1:8010. `docker compose down` stops the lab with the database and the app. Lab results stay in `lab/data/lab.sqlite3`.

- **Mock inference** is on by default when `TOGETHER_API_KEY` is empty. Use it to exercise the dashboard without spending tokens.
- Live runs use `Qwen/Qwen3.5-9B`, `temperature=0`, `reasoning.enabled=false`, `response_format=json_object`, streaming.
- Pricing fields are **editable assumptions** ($0.17 / $0.25 per million tokens), not invoices.
- **Period Debug** counts `judge.requested_period` and `say.testimony.scope` for the current experiment or all scored runs of the selected scenario.
- Refresh reconnects to the current experiment via SSE; it does not start a new Together job.
- **Run Again** force-starts a new experiment with the current controls.
- **Stop** prevents further runs.

## Tests

```bash
pytest tests/test_lab_contract.py tests/test_lab_evaluate.py tests/test_lab_api.py tests/test_lab_remembering.py
```

Results persist in `lab/data/lab.sqlite3` (gitignored). Export JSON or CSV from the dashboard; both include the Interaction State input context. CSV also includes each check’s `expected` and `actual` values.
