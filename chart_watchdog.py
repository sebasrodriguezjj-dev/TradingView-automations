#!/usr/bin/env python3
"""
Local watchdog for the SMART MONEY - GOOD MONEY chart runtime.

Purpose:
- Keep the chart executor alive in a local process outside Codex automations.
- Record health and retry cycles automatically.
- Give the automation stack a self-healing layer instead of waiting for manual rescue.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import chart_executor


WORKSPACE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = WORKSPACE_DIR / "chart_runtime"
STATE_PATH = RUNTIME_DIR / "chart_watchdog_state.json"
LOG_PATH = RUNTIME_DIR / "chart_watchdog.log"
POLL_SECONDS = 10
OWNER_NAME = "SMART MONEY - GOOD MONEY Chart Watchdog"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{now_iso()} | {OWNER_NAME} | {message}\n")


def save_state(payload: dict) -> None:
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def main() -> int:
    append_log("watchdog started")
    consecutive_failures = 0

    while True:
        state = {
            "owner": OWNER_NAME,
            "last_cycle_started_at": now_iso(),
            "consecutive_failures": consecutive_failures,
        }
        try:
            chart_executor.reconcile_all(force=False, dry_run=False)
            consecutive_failures = 0
            state["status"] = "healthy"
            state["last_cycle_finished_at"] = now_iso()
            save_state(state)
        except Exception as exc:
            consecutive_failures += 1
            state["status"] = "degraded"
            state["last_cycle_finished_at"] = now_iso()
            state["consecutive_failures"] = consecutive_failures
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            save_state(state)
            append_log(f"cycle failed: {type(exc).__name__}: {exc}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
