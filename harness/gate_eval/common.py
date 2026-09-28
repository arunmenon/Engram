"""Shared helpers: hashing, JSONL, git state, policy parsing, budget guard."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


class PreflightError(RuntimeError):
    """Raised when a run may not start. The message names the failed check."""


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj: Any) -> bytes:
    """Deterministic serialisation: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_sha256(record: dict) -> str:
    return sha256_bytes(canonical_json(record))


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON ({exc})") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def write_receipts(run_dir: Path) -> Path:
    """Write receipts.sha256 covering every other file in the run directory."""
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "receipts.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    out = run_dir / "receipts.sha256"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# --------------------------------------------------------------------------- git

def git_state(repo_root: Path) -> dict:
    """Return commit hash and cleanliness of the working tree."""
    def run(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()

    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain", "--untracked-files=normal")
    return {"commit": commit, "clean": status == "", "status": status}


def require_clean_tree(repo_root: Path, allow_dirty: bool = False) -> dict:
    state = git_state(repo_root)
    if not state["clean"] and not allow_dirty:
        raise PreflightError(
            "git working tree is not clean; commit or stash before a run. Dirty paths:\n" + state["status"]
        )
    return state


# ------------------------------------------------------------------------ policy

@dataclass
class Policy:
    """The subset of policy.md the harness enforces. Parsed, never edited."""

    version: str
    status: str
    tokens_per_run: int
    cost_usd_per_run: float
    wall_clock_h_per_run: float
    cost_usd_per_week: float
    runs_per_week: int
    concurrency: int
    permitted_datasets_raw: str
    dogfood_tenants_named: list[str] = field(default_factory=list)
    source_sha256: str = ""

    def snapshot(self) -> dict:
        return {
            "policy_version": self.version,
            "status": self.status,
            "budget_per_run": {
                "tokens": self.tokens_per_run,
                "cost_usd": self.cost_usd_per_run,
                "wall_clock_h": self.wall_clock_h_per_run,
            },
            "budget_per_week": {"cost_usd": self.cost_usd_per_week, "runs": self.runs_per_week},
            "concurrency": self.concurrency,
            "permitted_datasets": self.permitted_datasets_raw,
            "dogfood_tenants_named": self.dogfood_tenants_named,
            "policy_sha256": self.source_sha256,
        }


_KV = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<value>.*?)\s*(#.*)?$")


def _flow_map(text: str) -> dict[str, str]:
    inner = text.strip().strip("{}")
    out: dict[str, str] = {}
    for part in inner.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _flow_list(text: str) -> list[str]:
    inner = text.strip()
    if inner.startswith("["):
        inner = inner[1:]
    if inner.endswith("]"):
        inner = inner[:-1]
    return [p.strip() for p in inner.split(",") if p.strip()]


def parse_policy(path: Path) -> Policy:
    """Parse the fenced YAML block of policy.md with a minimal line parser.

    Only the keys the harness enforces are read. A missing key is a preflight
    failure rather than a default: caps must come from the policy, never from code.
    """
    raw = path.read_text(encoding="utf-8")
    status_match = re.search(r"^status:\s*(\S+)", raw, re.MULTILINE)
    if not status_match:
        raise PreflightError("policy.md has no top-level 'status:' line")
    fence = re.search(r"```yaml\n(.*?)```", raw, re.DOTALL)
    if not fence:
        raise PreflightError("policy.md has no fenced yaml block")
    kv: dict[str, str] = {}
    for line in fence.group(1).splitlines():
        m = _KV.match(line.strip())
        if m:
            kv[m.group("key")] = m.group("value")
    required = ["policy_version", "budget_per_run", "budget_per_week", "concurrency", "permitted_datasets"]
    missing = [k for k in required if k not in kv]
    if missing:
        raise PreflightError(f"policy.md is missing keys: {missing}")
    per_run = _flow_map(kv["budget_per_run"])
    per_week = _flow_map(kv["budget_per_week"])
    tenants = _flow_list(kv.get("dogfood_tenants_named", "[]"))
    return Policy(
        version=kv["policy_version"],
        status=status_match.group(1),
        tokens_per_run=int(per_run["tokens"]),
        cost_usd_per_run=float(per_run["cost_usd"]),
        wall_clock_h_per_run=float(per_run["wall_clock_h"]),
        cost_usd_per_week=float(per_week["cost_usd"]),
        runs_per_week=int(per_week["runs"]),
        concurrency=int(kv["concurrency"]),
        permitted_datasets_raw=kv["permitted_datasets"],
        dogfood_tenants_named=tenants,
        source_sha256=sha256_file(path),
    )


def require_policy_set(policy: Policy) -> None:
    if policy.status != "set":
        raise PreflightError(f"policy status is '{policy.status}', not 'set'; nothing executes")


# ------------------------------------------------------------------------ budget

@dataclass
class BudgetGuard:
    """Stops a run before a cap is exceeded. Checked before every call."""

    max_calls: int
    max_tokens: int
    max_wall_clock_s: float
    max_cost_usd: float
    usd_per_call: float | None
    started_at: float
    calls: int = 0
    tokens: int = 0
    cost_usd: float = 0.0

    def check_before_call(self, now: float) -> None:
        if self.calls >= self.max_calls:
            raise PreflightError(f"call cap reached ({self.max_calls})")
        if self.tokens >= self.max_tokens:
            raise PreflightError(f"token cap reached ({self.max_tokens})")
        if now - self.started_at >= self.max_wall_clock_s:
            raise PreflightError(f"wall-clock cap reached ({self.max_wall_clock_s / 3600:.2f} h)")
        projected = self.cost_usd + (self.usd_per_call or 0.0)
        if projected > self.max_cost_usd:
            raise PreflightError(f"cost cap would be exceeded ({projected:.4f} > {self.max_cost_usd} USD)")

    def record(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.tokens += int(input_tokens) + int(output_tokens)
        if self.usd_per_call is not None:
            self.cost_usd += self.usd_per_call

    def snapshot(self) -> dict:
        return {
            "calls": self.calls,
            "tokens": self.tokens,
            "cost_usd": self.cost_usd,
            "caps": {
                "calls": self.max_calls,
                "tokens": self.max_tokens,
                "wall_clock_s": self.max_wall_clock_s,
                "cost_usd": self.max_cost_usd,
            },
        }


def repo_root_from(path: Path) -> Path:
    """Walk up to the directory that contains .git."""
    for candidate in [path, *path.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise PreflightError(f"no git repository above {path}")


def env_api_key(name: str = "TYPESAFE_API_KEY") -> str | None:
    value = os.environ.get(name)
    return value if value else None
