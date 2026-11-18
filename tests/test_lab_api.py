"""Lab HTTP behaviour: mock inference, stop, export, no tool execution."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from lab.app import create_app
from lab.runner import ExperimentManager


async def _wait(client: AsyncClient, exp_id: str, timeout: float = 12) -> dict:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        exp = (await client.get(f"/api/experiments/{exp_id}")).json()
        if exp["status"] in {"completed", "stopped", "error"}:
            return exp
        await asyncio.sleep(0.05)
    raise AssertionError(f"experiment {exp_id} did not finish")


def _client(tmp_path: Path):
    app = create_app(tmp_path / "lab.sqlite3")
    return app, AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_mock_experiment_completes_and_exports(tmp_path: Path) -> None:
    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            started = await client.post(
                "/api/experiments",
                json={"runs": 2, "mock": True, "timeout_s": 30},
            )
            assert started.status_code == 200, started.text
            exp_id = started.json()["id"]
            meta = (await client.get("/api/meta")).json()
            assert "TOGETHER_API_KEY" not in str(meta)
            assert meta["has_api_key"] in {True, False}

            exp = await _wait(client, exp_id)
            assert exp["status"] == "completed"
            assert len(exp["runs"]) == 2
            assert all(r["status"] == "PASS" for r in exp["runs"])
            assert exp["metrics"]["strict_pass_rate"] == 100

            dumped = await client.get(f"/api/experiments/{exp_id}/export.json")
            assert dumped.status_code == 200
            payload = dumped.json()
            assert payload["id"] == exp_id
            first = payload["runs"][0]
            assert "judge" in first and "plan" in first and "say" in first
            assert "judgement" in (first.get("scores") or {})
            assert "plan_f1" in (first.get("scores") or {})
            assert "say" in (first.get("scores") or {})
            assert payload.get("input_context")
            assert "The Interaction State" in payload["input_context"]
            assert first.get("input_context") == payload["input_context"]
            assert payload.get("scenario_id")
            assert payload.get("scenario_title")

            csv = await client.get(f"/api/experiments/{exp_id}/export.csv")
            assert csv.status_code == 200
            assert "overall" in csv.text
            assert "judgement" in csv.text
            assert "plan_f1" in csv.text
            assert "say_json" in csv.text
            assert "input_context" in csv.text
            assert "The Interaction State" in csv.text
            assert "check_item_ids_expected" in csv.text
            assert "itm_0000000000000008" in csv.text
            assert "itm_0000000000000009" in csv.text
            assert "itm_000000000000000a" in csv.text
            assert "itm_000000000000000b" in csv.text
            assert csv.text.count("\n") >= 3

            again = await client.post(
                "/api/experiments",
                json={"runs": 1, "mock": True, "force": True},
            )
            assert again.status_code == 200
            assert again.json()["id"] != exp_id
            fresh = await _wait(client, again.json()["id"])
            assert fresh["status"] == "completed"

    asyncio.run(main())


def test_stop_prevents_additional_runs(tmp_path: Path) -> None:
    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            started = await client.post(
                "/api/experiments",
                json={"runs": 30, "mock": True},
            )
            exp_id = started.json()["id"]
            stopped = await client.post(f"/api/experiments/{exp_id}/stop")
            assert stopped.status_code == 200
            exp = await _wait(client, exp_id)
            assert exp["status"] == "stopped"
            assert len(exp["runs"]) < 30

            busy = await client.post(
                "/api/experiments",
                json={"runs": 20, "mock": True, "force": False},
            )
            # previous already stopped, so a new start is allowed
            assert busy.status_code in {200, 409}

    asyncio.run(main())


def test_concurrent_start_rejected_while_running(tmp_path: Path) -> None:
    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            first = await client.post("/api/experiments", json={"runs": 40, "mock": True})
            assert first.status_code == 200
            second = await client.post("/api/experiments", json={"runs": 2, "mock": True, "force": False})
            assert second.status_code == 409
            await client.post(f"/api/experiments/{first.json()['id']}/stop")
            await _wait(client, first.json()["id"])

    asyncio.run(main())


def test_sse_emits_progress(tmp_path: Path) -> None:
    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            started = await client.post("/api/experiments", json={"runs": 1, "mock": True})
            exp_id = started.json()["id"]
            seen = []
            async with client.stream("GET", f"/api/experiments/{exp_id}/events") as stream:
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        seen.append(line)
                    joined = "\n".join(seen)
                    if "snapshot" in joined or "run_completed" in joined or "finished" in joined:
                        break
            assert seen, "expected SSE payloads"

    asyncio.run(main())


def test_reload_does_not_start_a_new_experiment(tmp_path: Path) -> None:
    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            started = await client.post("/api/experiments", json={"runs": 1, "mock": True})
            exp_id = started.json()["id"]
            await _wait(client, exp_id)
            meta = (await client.get("/api/meta")).json()
            assert meta["current"]["id"] == exp_id
            listed = meta["history"]
            assert listed[0]["id"] == exp_id

    asyncio.run(main())


def test_live_requires_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)

    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            res = await client.post("/api/experiments", json={"runs": 1, "mock": False})
            assert res.status_code == 400

    asyncio.run(main())


def test_message_override_is_exported(tmp_path: Path) -> None:
    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            started = await client.post(
                "/api/experiments",
                json={
                    "runs": 1,
                    "mock": True,
                    "scenario": "remembering-02",
                    "message": "what did I complete today?",
                },
            )
            assert started.status_code == 200, started.text
            exp = await _wait(client, started.json()["id"])
            assert exp["status"] == "completed"
            assert exp["settings"]["message"] == "what did I complete today?"

            dumped = await client.get(f"/api/experiments/{exp['id']}/export.json")
            assert dumped.status_code == 200
            context = dumped.json()["input_context"]
            assert 'Current message:\n"what did I complete today?"' in context
            assert "What did I get done last week?" not in context
            assert "Hit the gym" in context

            csv = await client.get(f"/api/experiments/{exp['id']}/export.csv")
            assert "what did I complete today?" in csv.text

    asyncio.run(main())


def test_empty_message_keeps_scenario_text(tmp_path: Path) -> None:
    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            started = await client.post(
                "/api/experiments",
                json={"runs": 1, "mock": True, "scenario": "remembering-02", "message": "  "},
            )
            assert started.status_code == 200, started.text
            exp = await _wait(client, started.json()["id"])
            dumped = await client.get(f"/api/experiments/{exp['id']}/export.json")
            assert (
                'Current message:\n"What did I get done last week?"'
                in dumped.json()["input_context"]
            )
            assert dumped.json()["settings"]["message"] is None

    asyncio.run(main())


def test_stats_from_runs_groups_other_periods() -> None:
    from lab.periods import stats_from_runs

    def _run(start: str, end: str) -> dict:
        return {
            "evaluation": {
                "parsed": {
                    "judge": {
                        "understanding": {
                            "requested_period": {"start": start, "end": end}
                        }
                    },
                    "say": {"testimony": {"scope": {"start": start, "end": end}}},
                }
            }
        }

    stats = stats_from_runs(
        [
            _run("2026-11-08", "2026-11-14"),
            _run("2026-11-08", "2026-11-14"),
            _run("2026-11-09", "2026-11-15"),
            {"evaluation": {}},
        ]
    )
    assert stats["n"] == 3
    assert stats["scope"][0] == {
        "start": "2026-11-08",
        "end": "2026-11-14",
        "missing": False,
        "count": 2,
        "pct": 66.7,
    }
    assert stats["scope"][1]["start"] == "2026-11-09"
    assert stats["scope"][1]["count"] == 1


def test_period_stats_count_resolved_windows(tmp_path: Path) -> None:
    from lab.scenario import LAST_WEEK_END, LAST_WEEK_START

    async def main() -> None:
        app, client = _client(tmp_path)
        async with client:
            started = await client.post(
                "/api/experiments",
                json={"runs": 2, "mock": True, "scenario": "remembering-02"},
            )
            assert started.status_code == 200, started.text
            exp = await _wait(client, started.json()["id"])
            loaded = await client.get(f"/api/experiments/{exp['id']}")
            stats = loaded.json()["period_stats"]
            assert stats["n"] == 2
            assert stats["requested_period"][0]["start"] == LAST_WEEK_START
            assert stats["requested_period"][0]["end"] == LAST_WEEK_END
            assert stats["requested_period"][0]["count"] == 2
            assert stats["scope"][0]["start"] == LAST_WEEK_START
            assert stats["scope"][0]["end"] == LAST_WEEK_END
            assert stats["scope"][0]["count"] == 2

            across = await client.get("/api/period-stats?scenario=remembering-02")
            assert across.status_code == 200, across.text
            payload = across.json()
            assert payload["scenario_id"] == "remembering-02"
            assert payload["n"] == 2
            assert payload["scope"][0]["count"] == 2

    asyncio.run(main())


def test_tools_are_never_executed() -> None:
    import lab.runner as runner

    text = Path(runner.__file__).read_text()
    assert "tools.add_item" not in text
    assert "tools.update_item" not in text
    assert ".run(" not in inspect.getsource(ExperimentManager)
