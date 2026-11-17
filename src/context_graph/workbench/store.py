"""Durable local control records with compare-and-swap revisions.

This store holds authoring records only, never active runtime bindings.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path


class ConflictError(Exception):
    pass


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS drafts "
                "(id TEXT PRIMARY KEY, owner TEXT NOT NULL, revision INTEGER NOT NULL, "
                "record TEXT NOT NULL)"
            )
        path.chmod(0o600)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5)

    def list(self, owner: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT record FROM drafts WHERE owner=? ORDER BY rowid DESC", (owner,)
                )
            ]

    def get(self, owner: str, draft_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT record FROM drafts WHERE owner=? AND id=?", (owner, draft_id)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def create(self, owner: str, content: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": str(uuid4()),
            "revision": 1,
            "content": content,
            "proposal": None,
            "review": None,
            "validation": None,
            "sandbox": None,
            "approval": None,
            "history": [],
        }
        self.audit(record, "created", owner)
        with self.connect() as db:
            db.execute(
                "INSERT INTO drafts VALUES (?,?,?,?)", (record["id"], owner, 1, json.dumps(record))
            )
        return record

    @staticmethod
    def audit(record: dict[str, Any], action: str, owner: str) -> None:
        record["history"].append(
            {
                "action": action,
                "operator": owner,
                "at": datetime.now(UTC).isoformat(),
                "revision": record["revision"],
            }
        )
        record["history"] = record["history"][-200:]

    def put(self, owner: str, record: dict[str, Any], revision: int, action: str) -> dict[str, Any]:
        record["revision"] = revision + 1
        self.audit(record, action, owner)
        with self.connect() as db:
            changed = db.execute(
                "UPDATE drafts SET revision=?, record=? WHERE id=? AND owner=? AND revision=?",
                (record["revision"], json.dumps(record), record["id"], owner, revision),
            )
            if changed.rowcount != 1:
                raise ConflictError("Draft changed. Reload before applying this result.")
        return record

    def recover_jobs(self) -> None:
        """Called under the process lock before accepting requests after a restart."""
        with self.connect() as db:
            rows = db.execute("SELECT id, owner, revision, record FROM drafts").fetchall()
            for draft_id, owner, revision, raw in rows:
                record = json.loads(raw)
                if (record.get("job") or {}).get("status") != "running":
                    continue
                record["job"] = {
                    "status": "interrupted",
                    "error": "Server restarted; rerun the job.",
                }
                record["revision"] = revision + 1
                self.audit(record, "job_interrupted", owner)
                db.execute(
                    "UPDATE drafts SET revision=?, record=? WHERE id=?",
                    (revision + 1, json.dumps(record), draft_id),
                )
