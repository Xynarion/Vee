## Why ?

As a solo founder trying to build a one-person company that can compete with companies many times its size, I kept running into a problem.

Every time I switched back to one part of the company, I had to reconstruct where I left off.

And one of the first things I needed to recover was my sense of progress.

**What's completed?**

**What's still unresolved?**

The main thing I depended on to answer these questions was a todo list.

But as I worked, reality changed. The list kept falling behind, and I kept creating new lists.

Which meant answering those questions wasn't just time-consuming. The answers were often inaccurate, too.

I couldn't keep being responsible for both doing the work and maintaining the list.

So I decided to build a mechanism that could take over that responsibility.

## Company Progress Memory Mechanism V1

### Primary Responsibility

Keep the company's list (progress memory) up to date without depending on me to maintain it manually.

### Core Capabilities

**1. Notice when work changes**

Reconstruct changes in the state of my work through my brain dumps.

**2. Understand what those changes mean**

Determine whether an existing item needs updating, a new item needs creating, or clarification is required.

**3. Make sure the progress memory reflects those changes**

Maintain the company's list in a persistent database.

**4. Help me recover my sense of progress**

Present the company's progress memory in a way that helps me form a clear mental image of where the work stands at a glance.

## How I Got Here

I spent months researching what it would take to keep my company's progress memory up to date without depending on me.

The capabilities and requirements here came out of that research.

**[Read the full essay: I Can't Be the Only Memory of My Company](https://x.com/MoTheAgent/status/2099630288674697399)**

**Research chapters:** 

[Chapter 1](https://x.com/MoTheAgent/status/2101079146852147604) · [Chapter 2](https://x.com/MoTheAgent/status/2102167759350378536) · [Chapter 3](https://x.com/MoTheAgent/status/2103616043809927174) · [Chapter 4](https://x.com/MoTheAgent/status/2105066098433609808) · [Chapter 5](https://x.com/MoTheAgent/status/2106152758961410546) · [Chapter 6](https://x.com/MoTheAgent/status/2109776907848065107)

## Current Status

**M1 complete** — Postgres schema, Alembic, persistence smoke tests.

**M2 complete** — Telegram webhook (FastAPI): receive → store via ingress → reply `you said: …`.

**Next: M3** — assemble interaction state (message + recent turns + items + prompt).

Full milestone list (M1–M8): [MILESTONES.md](MILESTONES.md).

## M1 — local setup

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

Stop DB: `docker compose down` (add `-v` to wipe the volume).

## M2 — Telegram webhook

1. Put `TELEGRAM_BOT_TOKEN`, `WEBHOOK_URL`, and `TELEGRAM_WEBHOOK_SECRET` in `.env`.
2. Start DB (and migrate if needed), then the app:

```bash
docker compose up -d db app
# or on the host: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

3. Tunnel to the app (host ngrok):

```bash
ngrok http 8000
```

4. Set `WEBHOOK_URL` to the ngrok HTTPS origin (no path), restart the app so lifespan re-registers `setWebhook`.
5. Message the bot → expect `you said: …` and a row in `messages`.

Webhook path: `{WEBHOOK_URL}/telegram/webhook`. Health: `GET /health`.

Schema: `memory/models/`. Ops: `memory/operations/`. Transport: `api/telegram/`.