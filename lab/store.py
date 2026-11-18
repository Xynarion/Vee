"""SQLite persistence for experiments. Portable: one file, stdlib only."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
  id TEXT PRIMARY KEY,
  number INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL,
  settings_json TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  fixture_hash TEXT NOT NULL,
  summary_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS runs (
  experiment_id TEXT NOT NULL,
  run_number INTEGER NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  raw_response TEXT,
  evaluation_json TEXT,
  error TEXT,
  PRIMARY KEY (experiment_id, run_number)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def next_number(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(number), 0) + 1 AS n FROM experiments").fetchone()
    return int(row["n"])


def insert_experiment(conn: sqlite3.Connection, exp: Dict[str, Any]) -> None:
    conn.execute(
        """INSERT INTO experiments
           (id, number, created_at, status, settings_json, prompt_hash, fixture_hash, summary_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            exp["id"],
            exp["number"],
            exp["created_at"],
            exp["status"],
            json.dumps(exp["settings"]),
            exp["prompt_hash"],
            exp["fixture_hash"],
            json.dumps(exp.get("metrics") or {}),
        ),
    )
    conn.commit()


def update_experiment(conn: sqlite3.Connection, exp_id: str, **fields: Any) -> None:
    if "metrics" in fields:
        fields["summary_json"] = json.dumps(fields.pop("metrics"))
    if "settings" in fields:
        fields["settings_json"] = json.dumps(fields.pop("settings"))
    assignments = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE experiments SET {assignments} WHERE id = ?",
        [*fields.values(), exp_id],
    )
    conn.commit()


def upsert_run(conn: sqlite3.Connection, exp_id: str, run: Dict[str, Any]) -> None:
    conn.execute(
        """INSERT INTO runs
           (experiment_id, run_number, status, started_at, finished_at, raw_response, evaluation_json, error)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(experiment_id, run_number) DO UPDATE SET
             status=excluded.status,
             started_at=excluded.started_at,
             finished_at=excluded.finished_at,
             raw_response=excluded.raw_response,
             evaluation_json=excluded.evaluation_json,
             error=excluded.error
        """,
        (
            exp_id,
            run["run_number"],
            run.get("status") or "pending",
            run.get("started_at"),
            run.get("finished_at"),
            run.get("raw_response"),
            json.dumps(run["evaluation"]) if run.get("evaluation") else None,
            run.get("error"),
        ),
    )
    conn.commit()


def load_experiment(conn: sqlite3.Connection, exp_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone()
    if not row:
        return None
    runs = conn.execute(
        "SELECT * FROM runs WHERE experiment_id = ? ORDER BY run_number", (exp_id,)
    ).fetchall()
    return _exp_from_row(row, runs)


def stop_running(conn: sqlite3.Connection) -> None:
    conn.execute(
        "UPDATE experiments SET status = 'stopped' WHERE status = 'running'"
    )
    conn.commit()


def latest_experiment(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM experiments ORDER BY number DESC LIMIT 1").fetchone()
    if not row:
        return None
    return load_experiment(conn, row["id"])


def runs_for_scenario(conn: sqlite3.Connection, scenario_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """SELECT e.settings_json, r.evaluation_json
           FROM runs r
           JOIN experiments e ON e.id = r.experiment_id
           ORDER BY e.number, r.run_number"""
    ).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        settings = json.loads(row["settings_json"] or "{}")
        if settings.get("scenario") != scenario_id:
            continue
        evaluation = json.loads(row["evaluation_json"]) if row["evaluation_json"] else None
        out.append({"evaluation": evaluation})
    return out


def list_experiments(conn: sqlite3.Connection, limit: int = 30) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, number, created_at, status, summary_json FROM experiments ORDER BY number DESC LIMIT ?",
        (limit,),
    ).fetchall()
    out = []
    for row in rows:
        metrics = json.loads(row["summary_json"] or "{}")
        out.append(
            {
                "id": row["id"],
                "number": row["number"],
                "created_at": row["created_at"],
                "status": row["status"],
                "metrics": metrics,
            }
        )
    return out


def _exp_from_row(row: sqlite3.Row, run_rows: List[sqlite3.Row]) -> Dict[str, Any]:
    runs = []
    for r in run_rows:
        runs.append(
            {
                "run_number": r["run_number"],
                "status": r["status"],
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
                "raw_response": r["raw_response"],
                "evaluation": json.loads(r["evaluation_json"]) if r["evaluation_json"] else None,
                "error": r["error"],
            }
        )
    return {
        "id": row["id"],
        "number": row["number"],
        "created_at": row["created_at"],
        "status": row["status"],
        "settings": json.loads(row["settings_json"]),
        "prompt_hash": row["prompt_hash"],
        "fixture_hash": row["fixture_hash"],
        "metrics": json.loads(row["summary_json"] or "{}"),
        "runs": runs,
    }
