"""Vee Decision Lab — `uvicorn lab.app:app --port 8010`."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
from pathlib import Path
from typing import Optional

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from lab.runner import (  # noqa: E402
    DEFAULT_INPUT_RATE,
    DEFAULT_OUTPUT_RATE,
    DEFAULT_RUNS,
    DEFAULT_TIMEOUT_S,
    ExperimentManager,
    _env_key,
    _model,
    public_settings,
)
from lab.periods import stats_from_runs
from lab.scenario import get_scenario, list_scenarios, resolve_interaction_state
from lab import store  # noqa: E402

STATIC = Path(__file__).parent / "static"
DB_PATH = Path(os.getenv("LAB_DB_PATH") or Path(__file__).parent / "data" / "lab.sqlite3")


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


class StartBody(BaseModel):
    runs: int = DEFAULT_RUNS
    temperature: float = 0
    reasoning: bool = False
    json_mode: str = "json_object"
    timeout_s: float = DEFAULT_TIMEOUT_S
    mock: Optional[bool] = None
    input_rate: float = DEFAULT_INPUT_RATE
    output_rate: float = DEFAULT_OUTPUT_RATE
    force: bool = False
    scenario: Optional[str] = None
    message: Optional[str] = None


def create_app(db_path: Path | None = None) -> FastAPI:
    manager = ExperimentManager(db_path or DB_PATH)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await manager.close()

    app = FastAPI(title="Vee Decision Lab", lifespan=lifespan)
    app.state.manager = manager

    @app.get("/api/meta")
    def meta() -> dict:
        current = store.load_experiment(manager.conn, manager.current_id()) if manager.current_id() else store.latest_experiment(manager.conn)
        defaults = public_settings({})
        shown = get_scenario((current or {}).get("settings", {}).get("scenario") if current else defaults["scenario"])
        return {
            "model": _model(),
            "scenario": shown.title,
            "has_api_key": bool(_env_key()),
            "mock_default": not bool(_env_key()),
            "defaults": defaults,
            "running": manager.running(),
            "current": current,
            "history": store.list_experiments(manager.conn),
            "scenarios": list_scenarios(),
            "fixture": shown.interaction_state,
            "notes": [
                "Prompt contract is judge/plan/say (`llm.schema.Decision`).",
                "Prompt example JSON is instructional notation (and has a stray } in plan.tool_calls); the lab validates the intended object.",
                "If say.types includes testimony, say.testimony is required (not null).",
                "say.testimony.aim, view_reason, and scope_reason are required. purpose_reason is still required.",
                "Remembering: judge.requested_period, say.testimony.scope, and item_ids are scored independently against the clock.",
                "Planned add_item/update_item/search_items calls are scored as data and never executed.",
                "json_object is the default response format. json_schema is optional and model-dependent.",
            ],
        }

    @app.post("/api/experiments")
    async def start(body: StartBody) -> dict:
        settings = body.model_dump()
        if settings.get("mock") is None:
            settings["mock"] = not bool(_env_key())
        force = bool(settings.pop("force"))
        try:
            exp = await manager.start(settings, force=force)
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return exp

    @app.post("/api/experiments/{exp_id}/stop")
    async def stop(exp_id: str) -> dict:
        return await manager.stop(exp_id)

    @app.get("/api/experiments/{exp_id}")
    def get_experiment(exp_id: str) -> dict:
        exp = store.load_experiment(manager.conn, exp_id)
        if not exp:
            raise HTTPException(404, "experiment not found")
        exp["period_stats"] = stats_from_runs(exp.get("runs") or [])
        return exp

    @app.get("/api/period-stats")
    def period_stats(scenario: Optional[str] = None) -> dict:
        shown = get_scenario(scenario)
        runs = store.runs_for_scenario(manager.conn, shown.id)
        return {
            "scenario_id": shown.id,
            "scenario_title": shown.title,
            **stats_from_runs(runs),
        }

    @app.get("/api/experiments/{exp_id}/events")
    async def events(exp_id: str, request: Request) -> StreamingResponse:
        q = await manager.subscribe(exp_id)

        async def gen():
            try:
                while not manager._closing.is_set():
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(q.get(), timeout=2)
                    except asyncio.TimeoutError:
                        yield "event: ping\ndata: {}\n\n"
                        continue
                    yield f"event: lab\ndata: {json.dumps(event)}\n\n"
                    if event.get("type") == "finished":
                        break
            finally:
                manager.unsubscribe(exp_id, q)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/experiments/{exp_id}/export.json")
    def export_json(exp_id: str) -> dict:
        exp = store.load_experiment(manager.conn, exp_id)
        if not exp:
            raise HTTPException(404, "experiment not found")
        settings = exp.get("settings") or {}
        scenario = get_scenario(settings.get("scenario"))
        input_context = resolve_interaction_state(
            scenario.id, settings.get("message")
        )
        runs = []
        for run in exp.get("runs") or []:
            ev = run.get("evaluation") or {}
            parsed = ev.get("parsed") or {}
            row = dict(run)
            row["input_context"] = input_context
            row["judge"] = parsed.get("judge")
            row["plan"] = parsed.get("plan")
            row["say"] = parsed.get("say")
            row["scores"] = ev.get("scores")
            row["fail_kind"] = ev.get("fail_kind")
            row["checks"] = ev.get("checks")
            runs.append(row)
        return {
            **exp,
            "scenario_id": scenario.id,
            "scenario_title": scenario.title,
            "input_context": input_context,
            "runs": runs,
        }

    @app.get("/api/experiments/{exp_id}/export.csv")
    def export_csv(exp_id: str) -> StreamingResponse:
        exp = store.load_experiment(manager.conn, exp_id)
        if not exp:
            raise HTTPException(404, "experiment not found")
        check_ids: list[str] = []
        seen: set[str] = set()
        for run in exp.get("runs") or []:
            ev = run.get("evaluation") or {}
            for group in ("judge", "plan", "say"):
                for check in (ev.get("checks") or {}).get(group) or []:
                    cid = check.get("id")
                    if cid and cid not in seen:
                        seen.add(cid)
                        check_ids.append(cid)
        buf = io.StringIO()
        writer = csv.writer(buf)
        settings = exp.get("settings") or {}
        scenario = get_scenario(settings.get("scenario"))
        input_context = resolve_interaction_state(
            scenario.id, settings.get("message")
        )
        check_headers: list[str] = []
        for cid in check_ids:
            check_headers.extend(
                [f"check_{cid}", f"check_{cid}_expected", f"check_{cid}_actual"]
            )
        writer.writerow(
            [
                "run",
                "status",
                "fail_kind",
                "overall",
                "judgement",
                "plan_f1",
                "say",
                "json_valid",
                "schema_valid",
                "latency_s",
                "ttft_s",
                "input_tokens",
                "output_tokens",
                "cost_usd",
                "error",
                "scenario_id",
                "scenario_title",
                "input_context",
                "judge",
                "plan",
                "say_json",
            ]
            + check_headers
        )
        for run in exp["runs"]:
            ev = run.get("evaluation") or {}
            scores = ev.get("scores") or {}
            gates = ev.get("gates") or {}
            lat = ev.get("latency") or {}
            usage = ev.get("usage") or {}
            parsed = ev.get("parsed") or {}
            checks = ev.get("checks") or {}
            by_id = {
                c.get("id"): c
                for group in ("judge", "plan", "say")
                for c in checks.get(group) or []
                if c.get("id")
            }
            check_cells: list[str] = []
            for cid in check_ids:
                row_check = by_id.get(cid) or {}
                check_cells.extend(
                    [
                        row_check.get("status") or "",
                        _csv_cell(row_check.get("expected")),
                        _csv_cell(row_check.get("actual")),
                    ]
                )
            writer.writerow(
                [
                    run["run_number"],
                    run.get("status"),
                    ev.get("fail_kind") or "",
                    scores.get("overall"),
                    scores.get("judgement"),
                    scores.get("plan_f1"),
                    scores.get("say"),
                    gates.get("json_valid"),
                    gates.get("schema_valid"),
                    lat.get("total_s"),
                    lat.get("ttft_s"),
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    usage.get("cost_usd"),
                    run.get("error") or ev.get("json_error") or "",
                    scenario.id,
                    scenario.title,
                    input_context,
                    json.dumps(parsed.get("judge"), ensure_ascii=False) if parsed.get("judge") is not None else "",
                    json.dumps(parsed.get("plan"), ensure_ascii=False) if parsed.get("plan") is not None else "",
                    json.dumps(parsed.get("say"), ensure_ascii=False) if parsed.get("say") is not None else "",
                ]
                + check_cells
            )
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=vee-lab-{exp_id}.csv"},
        )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
