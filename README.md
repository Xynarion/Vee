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

**M1 complete** — Postgres schema, Alembic migrations, and persistence smoke tests pass.

The mechanism can create users/channels from a platform identity, store conversation turns, and write items + history.

**Next: M2** — Telegram transport (receive message → store → reply).

Full milestone list (M1–M8): [MILESTONES.md](MILESTONES.md).

## M1 — local setup

Postgres runs in Docker. Python (venv) stays on the host for now.

```bash
cd company-progress-memory-mechanism
cp .env.example .env

# Start Postgres
docker compose up -d db

# App deps on the host
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Schema (pick one)
alembic upgrade head
# or: docker compose --profile migrate run --rm migrate

pytest
```

Stop DB: `docker compose down` (add `-v` to wipe the volume).

Schema lives in `memory/models/`. Migrations in `alembic/versions/`. Runtime engine/session in `memory/db.py`.