"""Together inference + sequential experiment runner. Tools are never executed."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from llm.prompt import SYSTEM_PROMPT
from lab import store
from lab.evaluate import aggregate, evaluate_decision
from lab.scenario import (
    DEFAULT_SCENARIO_ID,
    fixture_hash,
    get_scenario,
    prompt_hash,
    resolve_interaction_state,
)

MESSAGE_MAX_LEN = 2000

Listener = Callable[[Dict[str, Any]], Awaitable[None]]

DEFAULT_MODEL = "Qwen/Qwen3.5-9B"
DEFAULT_INPUT_RATE = 0.17
DEFAULT_OUTPUT_RATE = 0.25
DEFAULT_TIMEOUT_S = 90.0
DEFAULT_RUNS = 10


def _env_key() -> str:
    return (os.getenv("TOGETHER_API_KEY") or "").strip()


def _model() -> str:
    return (os.getenv("TOGETHER_MODEL") or DEFAULT_MODEL).strip()


def public_settings(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Never include secrets."""
    return {
        "model": raw.get("model") or _model(),
        "runs": int(raw.get("runs") or DEFAULT_RUNS),
        "temperature": float(raw.get("temperature") if raw.get("temperature") is not None else 0),
        "reasoning": bool(raw.get("reasoning")),
        "json_mode": raw.get("json_mode") or "json_object",
        "timeout_s": float(raw.get("timeout_s") or DEFAULT_TIMEOUT_S),
        "mock": bool(raw.get("mock", not bool(_env_key()))),
        "input_rate": float(raw.get("input_rate") if raw.get("input_rate") is not None else DEFAULT_INPUT_RATE),
        "output_rate": float(raw.get("output_rate") if raw.get("output_rate") is not None else DEFAULT_OUTPUT_RATE),
        "scenario": get_scenario(raw.get("scenario") or DEFAULT_SCENARIO_ID).id,
        "message": _optional_message(raw.get("message")),
    }


def _optional_message(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class ExperimentManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = store.connect(db_path)
        self._lock = asyncio.Lock()
        self._stop: Dict[str, asyncio.Event] = {}
        self._task: Optional[asyncio.Task] = None
        self._current_id: Optional[str] = None
        self._subs: Dict[str, List[asyncio.Queue]] = {}
        self._streams: Dict[str, str] = {}
        self._closing = asyncio.Event()
        store.stop_running(self.conn)

    def current_id(self) -> Optional[str]:
        return self._current_id

    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def subscribe(self, exp_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.setdefault(exp_id, []).append(q)
        snapshot = store.load_experiment(self.conn, exp_id)
        if snapshot:
            await q.put(
                {
                    "type": "snapshot",
                    "experiment": snapshot,
                    "stream": self._streams.get(exp_id, ""),
                }
            )
        return q

    def unsubscribe(self, exp_id: str, q: asyncio.Queue) -> None:
        subs = self._subs.get(exp_id) or []
        if q in subs:
            subs.remove(q)

    async def _emit(self, exp_id: str, event: Dict[str, Any]) -> None:
        for q in list(self._subs.get(exp_id, [])):
            await q.put(event)

    async def start(self, raw_settings: Dict[str, Any], *, force: bool = False) -> Dict[str, Any]:
        settings = public_settings(raw_settings)
        if settings["runs"] < 1 or settings["runs"] > 100:
            raise ValueError("runs must be 1–100")
        if settings["json_mode"] not in {"json_object", "json_schema"}:
            raise ValueError("json_mode must be json_object or json_schema")
        if not settings["mock"] and not _env_key():
            raise ValueError("TOGETHER_API_KEY is required unless mock is enabled")
        if settings.get("message") and len(settings["message"]) > MESSAGE_MAX_LEN:
            raise ValueError(f"message must be {MESSAGE_MAX_LEN} characters or fewer")

        async with self._lock:
            if self.running() and not force:
                raise RuntimeError("an experiment is already running")
            if self.running() and force and self._current_id:
                self._stop.setdefault(self._current_id, asyncio.Event()).set()
                self._task.cancel()
                try:
                    await self._task
                except (asyncio.CancelledError, Exception):
                    pass
                store.update_experiment(self.conn, self._current_id, status="stopped")

            exp = {
                "id": uuid.uuid4().hex[:12],
                "number": store.next_number(self.conn),
                "created_at": store.now(),
                "status": "running",
                "settings": settings,
                "prompt_hash": prompt_hash(SYSTEM_PROMPT),
                "fixture_hash": fixture_hash(
                    resolve_interaction_state(
                        settings["scenario"], settings.get("message")
                    )
                ),
                "metrics": {},
                "runs": [],
            }
            store.insert_experiment(self.conn, exp)
            self._current_id = exp["id"]
            self._streams[exp["id"]] = ""
            self._stop[exp["id"]] = asyncio.Event()
            self._task = asyncio.create_task(self._run_experiment(exp["id"], settings))
            await self._emit(exp["id"], {"type": "started", "experiment": exp})
            return exp

    async def stop(self, exp_id: str) -> Dict[str, Any]:
        flag = self._stop.get(exp_id)
        if flag:
            flag.set()
        return store.load_experiment(self.conn, exp_id) or {"id": exp_id, "status": "unknown"}

    async def close(self) -> None:
        self._closing.set()
        for flag in self._stop.values():
            flag.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        store.stop_running(self.conn)
        for qs in self._subs.values():
            for q in qs:
                try:
                    q.put_nowait({"type": "finished", "status": "stopped"})
                except asyncio.QueueFull:
                    pass

    async def _run_experiment(self, exp_id: str, settings: Dict[str, Any]) -> None:
        try:
            for i in range(1, settings["runs"] + 1):
                if self._stop[exp_id].is_set():
                    store.update_experiment(self.conn, exp_id, status="stopped")
                    await self._finish(exp_id, "stopped")
                    return
                await self._run_one(exp_id, i, settings)
            store.update_experiment(self.conn, exp_id, status="completed")
            await self._finish(exp_id, "completed")
        except asyncio.CancelledError:
            store.update_experiment(self.conn, exp_id, status="stopped")
            await self._finish(exp_id, "stopped")
            raise
        except Exception as exc:  # noqa: BLE001
            store.update_experiment(self.conn, exp_id, status="error")
            await self._emit(exp_id, {"type": "error", "error": str(exc)})
            await self._finish(exp_id, "error")

    async def _finish(self, exp_id: str, status: str) -> None:
        exp = store.load_experiment(self.conn, exp_id)
        metrics = aggregate(exp["runs"] if exp else [])
        store.update_experiment(self.conn, exp_id, status=status, metrics=metrics)
        if exp:
            exp["status"] = status
            exp["metrics"] = metrics
        await self._emit(exp_id, {"type": "finished", "status": status, "experiment": exp})
        if self._current_id == exp_id:
            self._task = None

    async def _run_one(self, exp_id: str, run_number: int, settings: Dict[str, Any]) -> None:
        run = {
            "run_number": run_number,
            "status": "running",
            "started_at": store.now(),
            "finished_at": None,
            "raw_response": "",
            "evaluation": None,
            "error": None,
        }
        store.upsert_run(self.conn, exp_id, run)
        self._streams[exp_id] = ""
        await self._emit(
            exp_id,
            {
                "type": "run_started",
                "run_number": run_number,
                "total": settings["runs"],
            },
        )

        chunks: List[str] = []
        usage: Dict[str, Any] = {}
        latency = {"ttft_s": None, "total_s": None, "api_error": False}
        t0 = time.perf_counter()

        async def on_delta(text: str) -> None:
            if latency["ttft_s"] is None and text:
                latency["ttft_s"] = round(time.perf_counter() - t0, 4)
            chunks.append(text)
            self._streams[exp_id] = "".join(chunks)
            await self._emit(
                exp_id,
                {"type": "stream", "run_number": run_number, "delta": text},
            )

        error = None
        finish_reason = None
        try:
            scenario = get_scenario(settings.get("scenario"))
            interaction_state = resolve_interaction_state(
                scenario.id, settings.get("message")
            )
            if settings["mock"]:
                finish_reason = await _mock_stream(
                    on_delta, self._stop[exp_id], scenario.golden()
                )
            else:
                finish_reason, usage = await _together_stream(
                    on_delta,
                    settings,
                    self._stop[exp_id],
                    interaction_state,
                )
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            latency["api_error"] = True

        latency["total_s"] = round(time.perf_counter() - t0, 4)
        raw = "".join(chunks)
        if finish_reason and finish_reason not in {"stop", "eos", None}:
            error = error or f"truncated finish_reason={finish_reason}"

        evaluation = evaluate_decision(
            raw,
            input_rate=settings["input_rate"],
            output_rate=settings["output_rate"],
            usage=usage,
            latency=latency,
            error=error,
            scenario_id=settings.get("scenario"),
        )
        run.update(
            {
                "status": evaluation["status"],
                "finished_at": store.now(),
                "raw_response": raw,
                "evaluation": evaluation,
                "error": error,
            }
        )
        store.upsert_run(self.conn, exp_id, run)
        exp = store.load_experiment(self.conn, exp_id)
        metrics = aggregate(exp["runs"] if exp else [])
        store.update_experiment(self.conn, exp_id, metrics=metrics)
        self._streams[exp_id] = ""
        await self._emit(
            exp_id,
            {
                "type": "run_completed",
                "run": run,
                "metrics": metrics,
                "current": run_number,
                "total": settings["runs"],
            },
        )


async def _mock_stream(on_delta, stop: asyncio.Event, payload: Dict[str, Any]) -> str:
    text = json.dumps(payload, indent=2)
    for i in range(0, len(text), 48):
        if stop.is_set():
            break
        await on_delta(text[i : i + 48])
        await asyncio.sleep(0.004)
    return "stop"


async def _together_stream(
    on_delta,
    settings: Dict[str, Any],
    stop: asyncio.Event,
    interaction_state: str,
) -> tuple[Optional[str], Dict[str, Any]]:
    """Official Together SDK in a worker thread; chunks hop back via the event loop."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    timeout = settings["timeout_s"]

    def worker() -> None:
        usage: Dict[str, Any] = {}
        reason = None
        try:
            from together import Together

            client = Together(api_key=_env_key())
            # Together 2.9 create() has no stream_options kwarg (that is OpenAI-only).
            kwargs: Dict[str, Any] = {
                "model": settings["model"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": interaction_state},
                ],
                "temperature": settings["temperature"],
                "stream": True,
                "response_format": _response_format(settings["json_mode"]),
                "reasoning": {"enabled": bool(settings["reasoning"])},
                "timeout": timeout,
            }
            try:
                stream = client.chat.completions.create(**kwargs)
            except TypeError:
                kwargs.pop("reasoning", None)
                stream = client.chat.completions.create(**kwargs)
            for chunk in stream:
                if stop.is_set():
                    break
                choice = (chunk.choices or [None])[0]
                if choice is not None:
                    delta = getattr(choice, "delta", None)
                    content = getattr(delta, "content", None) if delta is not None else None
                    if content:
                        loop.call_soon_threadsafe(queue.put_nowait, ("delta", content))
                    reason = getattr(choice, "finish_reason", None) or reason
                u = getattr(chunk, "usage", None)
                if u is not None:
                    prompt = getattr(u, "prompt_tokens", None)
                    completion = getattr(u, "completion_tokens", None)
                    usage = {
                        "input_tokens": prompt if prompt is not None else None,
                        "output_tokens": completion if completion is not None else None,
                    }
            loop.call_soon_threadsafe(queue.put_nowait, ("done", reason, usage))
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))

    threading.Thread(target=worker, daemon=True).start()
    deadline = time.perf_counter() + timeout
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            raise TimeoutError(f"Together request exceeded {timeout}s")
        try:
            item = await asyncio.wait_for(queue.get(), timeout=remaining)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"Together request exceeded {timeout}s") from exc
        kind = item[0]
        if kind == "delta":
            await on_delta(item[1])
        elif kind == "done":
            return item[1], item[2]
        elif kind == "error":
            raise RuntimeError(item[1])


def _response_format(mode: str) -> Dict[str, Any]:
    if mode == "json_schema":
        from lab.contract import LabDecision

        return {
            "type": "json_schema",
            "json_schema": {
                "name": "vee_decision",
                "schema": LabDecision.model_json_schema(),
            },
        }
    return {"type": "json_object"}
