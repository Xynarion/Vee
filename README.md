## Why ?

As a solo founder trying to build a one-person company that can compete with companies many times its size, I kept running into a problem.

Every time I switched back to one part of the company, I had to reconstruct where I left off.

In that reconstruction process, one of the first things I needed to recover was my sense of progress.

**What's completed?**
**What's still unresolved?**

anaswer above partyly helped me answer where i left things off last time. 

So to answer them, the main thing I depended on a was a todo list.

But as I worked, reality changed. 
The list kept falling behind, and I kept creating new lists.

Which meant answering those questions weren't just time-consuming. 
The answers were often inaccurate, too.

I couldn't keep being responsible for both doing the work and maintaining the list.

So I decided to build a mechanism that could take over that responsibility.

## Company Progress Memory Mechanism V1

### Primary Responsibility

Vee is the company's witness. Vee witnesses changes in the work and, when asked, testifies from the record.

Keep the company's progress memory up to date, and help me remember that progress whenever I ask, without depending on me to maintain it manually.

When a message is outside this responsibility, Vee stays silent.

### Core Capabilities

**1. Notice when work changes**

Reconstruct changes in the state of my work through my brain dumps.

**2. Understand what those changes mean**

Determine whether an existing item needs updating, a new item needs creating, or a clarification is required. If a change is unclear, Vee asks.

**3. Make sure the progress memory reflects those changes**

Maintain the company's list in a persistent database.

**4. Help me recover my sense of progress**

Present the company's progress memory in a way that helps me form a clear mental image of where the work stands at a glance. Vee speaks only from what was recorded. Nothing invented. No advice.

## How I Got Here

I spent months researching what it would take to keep my company's progress memory up to date without depending on me.

The capabilities and requirements here came out of that research.

**[Read the full essay: I Can't Be the Only Memory of My Company](https://x.com/MoTheAgent/status/2099630288674697399)**

**Research chapters:** 

[Chapter 1](https://x.com/MoTheAgent/status/2101079146852147604) · [Chapter 2](https://x.com/MoTheAgent/status/2102167759350378536) · [Chapter 3](https://x.com/MoTheAgent/status/2103616043809927174) · [Chapter 4](https://x.com/MoTheAgent/status/2105066098433609808) · [Chapter 5](https://x.com/MoTheAgent/status/2106152758961410546) · [Chapter 6](https://x.com/MoTheAgent/status/2109776907848065107)

**[What Kind of Identity Would Fit My Company's Progress Memory Mechanism?](https://x.com/MoTheAgent/status/2115590446076588391)**

## Current Status

**M1 complete** — Foundation: Vee & Company Progress Memory. Postgres schema, Alembic, persistence tests.

**M2 complete** — Communication: Telegram Bot. Receive, store, and reply `you said: …`.

**M3 complete** — Interaction State Assembly. Current message, Founder/Vee turns, Progress Memory, clock, and this and last calendar week.

**M4 complete** — Vee's Central Decision-Making. One `Qwen/Qwen3.5-9B` call returns a Judge–Plan–Say decision. Validation accepts it, or returns the clarification fallback. No retry. Telegram still echoes.

**M5 in progress** — Execute Decisions & Maintain Progress Memory.

**Lab:** local Together benchmark dashboard — see [lab/README.md](lab/README.md). `docker compose up` serves it at http://127.0.0.1:8010

Full milestone list (M1–M8): [MILESTONES.md](MILESTONES.md).

## M1 — Foundation: Vee & Company Progress Memory

Postgres runs in Docker. App can run on the host or in Compose.

```bash
cd company-progress-memory-mechanism
cp .env.example .env   # fill secrets; keep .env out of git

docker compose up -d db

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
# or: docker compose --profile migrate run --rm migrate

pytest
```

Stop the stack: `docker compose down` (add `-v` to wipe the Postgres volume). Lab results in `lab/data/` stay.

## M2 — Communication: Telegram Bot

1. Put `TELEGRAM_BOT_TOKEN`, `WEBHOOK_URL`, and `TELEGRAM_WEBHOOK_SECRET` in `.env`.
2. Start DB (and migrate if needed), then the app:

```bash
docker compose up -d
# or on the host: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

3. Tunnel to the app (host ngrok):

```bash
ngrok http 8000
```

4. Set `WEBHOOK_URL` to the ngrok HTTPS origin (no path), restart the app so lifespan re-registers `setWebhook`.
5. Message the bot → expect `you said: …` and a row in `messages`.

Webhook path: `{WEBHOOK_URL}/telegram/webhook`. Health: `GET /health`.

## M3 — Interaction State Assembly

After ingress, `assemble_interaction_state(turn)` loads recent messages (excluding the current one), Progress Memory items (all statuses, with history), and renders the same Interaction State plate as the lab scenarios: current message, Founder/Vee conversation, items, clock, and this/last calendar week.

```bash
pytest tests/test_interaction_state.py
```

Schema: `memory/models/`. Ops: `memory/operations/` (incl. `state.py`). Transport: `api/telegram/`.

## M4 — Vee's Central Decision-Making

`infer_decision` sends the system prompt and the rendered Interaction State to `Qwen/Qwen3.5-9B` once. `accept_model_output` checks the JSON against the Judge–Plan–Say contract. A bad response becomes a clarification with no tool calls. There is no retry. The webhook logs the decision. Telegram still replies with the echo.

```bash
pytest tests/test_llm_contract.py tests/test_llm_infer.py tests/test_telegram_webhook.py
```

Contract: `llm/schema.py`. Inference: `llm/infer.py`. Parse and validate: `llm/validate.py`.