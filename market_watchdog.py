#!/usr/bin/env python3
"""
Local watchdog for the SMART MONEY - GOOD MONEY market runtime.

Purpose:
- Keep the TradingView structured live-state reader alive outside Codex
  automations.
- Refresh local live-state JSON so automations can read live market context
  without talking to TradingView directly.
- Record health and degraded cycles instead of waiting for manual rescue.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import market_snapshotter


WORKSPACE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = WORKSPACE_DIR / "market_runtime"
STATE_PATH = RUNTIME_DIR / "market_watchdog_state.json"
LOG_PATH = RUNTIME_DIR / "market_watchdog.log"
POLL_SECONDS = 10
OWNER_NAME = "SMART MONEY - GOOD MONEY Market Watchdog"


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
            market_snapshotter.refresh_live_state_statuses()
            results = market_snapshotter.capture_all(dry_run=False)
            market_snapshotter.refresh_live_state_statuses()
            unhealthy_symbols = [
                result
                for result in results
                if result.get("data_confidence") == "DATA_DEGRADED"
            ]
            runtime_payload = market_snapshotter.update_runtime_state(
                cycle_status="healthy",
                symbol_results=results,
                expected_symbols=len(market_snapshotter.SYMBOLS),
            )
            consecutive_failures = 0
            state["status"] = "healthy"
            state["consecutive_failures"] = consecutive_failures
            state["data_mode"] = "structured_only"
            state["symbols"] = results
            state["all_symbols_valid"] = runtime_payload.get("all_symbols_valid")
            state["workflow_stalled"] = runtime_payload.get("workflow_stalled")
            state["recovery_pending"] = runtime_payload.get("recovery_pending")
            state["recovery_gate_status"] = runtime_payload.get("recovery_gate_status")
            state["last_full_valid_cycle_at"] = runtime_payload.get("last_full_valid_cycle_at")
            state["stall_started_at"] = runtime_payload.get("stall_started_at")
            state["recovery_requested_at"] = runtime_payload.get("recovery_requested_at")
            if unhealthy_symbols:
                state["degraded_symbols"] = [
                    {
                        "symbol": result.get("symbol"),
                        "status": result.get("status"),
                        "data_confidence": result.get("data_confidence"),
                        "capture_attempts": result.get("capture_attempts"),
                        "recovery_step_used": result.get("recovery_step_used"),
                        "last_error": result.get("last_error"),
                    }
                    for result in unhealthy_symbols
                ]
                dependency_statuses = [
                    classify_dependency_status(str(result.get("last_error") or ""))
                    for result in unhealthy_symbols
                ]
                state["dependency_status"] = next(
                    (status for status in dependency_statuses if status),
                    "data_degraded",
                )
            state["last_cycle_finished_at"] = now_iso()
            state["heartbeat_at"] = now_iso()
            state["last_cycle_duration_seconds"] = round(
                time.monotonic() - cycle_started_monotonic,
                3,
            )
            save_state(state)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            stale_results = market_snapshotter.refresh_live_state_statuses()
            runtime_payload = market_snapshotter.update_runtime_state(
                cycle_status="degraded",
                symbol_results=stale_results,
                last_error=last_error,
                expected_symbols=len(market_snapshotter.SYMBOLS),
            )
            consecutive_failures += 1
            state["status"] = "degraded"
            state["data_mode"] = "structured_only"
            state["symbols"] = stale_results
            state["last_cycle_finished_at"] = now_iso()
            state["consecutive_failures"] = consecutive_failures
            state["all_symbols_valid"] = runtime_payload.get("all_symbols_valid")
            state["workflow_stalled"] = runtime_payload.get("workflow_stalled")
            state["recovery_pending"] = runtime_payload.get("recovery_pending")
            state["recovery_gate_status"] = runtime_payload.get("recovery_gate_status")
            state["last_full_valid_cycle_at"] = runtime_payload.get("last_full_valid_cycle_at")
            state["stall_started_at"] = runtime_payload.get("stall_started_at")
            state["recovery_requested_at"] = runtime_payload.get("recovery_requested_at")
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
