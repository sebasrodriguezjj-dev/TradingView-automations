#!/usr/bin/env python3
"""
Local watchdog for the SMART MONEY - GOOD MONEY chart runtime.

Purpose:
- Keep the chart executor alive in a local process outside Codex automations.
- Record health and retry cycles automatically.
- Give the automation stack a self-healing layer instead of waiting for manual rescue.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

import chart_executor
import tv_gateway


WORKSPACE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = WORKSPACE_DIR / "chart_runtime"
STATE_PATH = RUNTIME_DIR / "chart_watchdog_state.json"
LOG_PATH = RUNTIME_DIR / "chart_watchdog.log"
POLL_SECONDS = 10
OWNER_NAME = "SMART MONEY - GOOD MONEY Chart Watchdog"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def classify_dependency_status(error_text: str | None) -> str | None:
    if not error_text:
        return None
    if "TvLockTimeout" in error_text or "TradingView gateway lock" in error_text:
        return "tradingview_lock_blocked"
    if "TimeoutExpired" in error_text and "tradingview-mcp" in error_text:
        return "tradingview_mcp_timeout"
    if "TimeoutExpired" in error_text and "node" in error_text:
        return "tradingview_mcp_timeout"
    if "TvCliError" in error_text:
        return "tradingview_cli_error"
    return "runtime_error"


def append_log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{now_iso()} | {OWNER_NAME} | {message}\n")


def save_state(payload: dict) -> None:
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def reload_runtime_modules() -> None:
    global chart_executor, tv_gateway

    # Keep the long-running watchdog aligned with the latest runtime contract
    # so chart-marking rule changes apply without a manual process restart.
    tv_gateway = importlib.reload(tv_gateway)
    chart_executor = importlib.reload(chart_executor)


def refresh_heartbeat(watchdog_pid: int, watchdog_started_at: str) -> None:
    payload: dict = {}
    if STATE_PATH.exists():
        try:
            payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    payload.update(
        {
            "owner": OWNER_NAME,
            "watchdog_pid": watchdog_pid,
            "watchdog_started_at": watchdog_started_at,
            "heartbeat_at": now_iso(),
            "process_status": "running",
        }
    )
    save_state(payload)


def main() -> int:
    append_log("watchdog started")
    consecutive_failures = 0
    watchdog_started_at = now_iso()
    watchdog_pid = os.getpid()

    while True:
        cycle_started_monotonic = time.monotonic()
        refresh_heartbeat(watchdog_pid, watchdog_started_at)
        state = {
            "owner": OWNER_NAME,
            "watchdog_pid": watchdog_pid,
            "watchdog_started_at": watchdog_started_at,
            "heartbeat_at": now_iso(),
            "last_cycle_started_at": now_iso(),
            "consecutive_failures": consecutive_failures,
        }
        try:
            reload_runtime_modules()
            chart_executor.reconcile_all(force=False, dry_run=False)
            consecutive_failures = 0
            state["status"] = "healthy"
            state["last_cycle_finished_at"] = now_iso()
            state["heartbeat_at"] = now_iso()
            state["last_cycle_duration_seconds"] = round(
                time.monotonic() - cycle_started_monotonic,
                3,
            )
            save_state(state)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            consecutive_failures += 1
            state["status"] = "degraded"
            state["last_cycle_finished_at"] = now_iso()
            state["consecutive_failures"] = consecutive_failures
            state["last_error"] = last_error
            state["dependency_status"] = classify_dependency_status(last_error)
            state["heartbeat_at"] = now_iso()
            state["last_cycle_duration_seconds"] = round(
                time.monotonic() - cycle_started_monotonic,
                3,
            )
            save_state(state)
            append_log(f"cycle failed: {last_error}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
