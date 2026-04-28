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
            market_snapshotter.refresh_live_state_statuses()
            results = market_snapshotter.capture_all(dry_run=False)
            market_snapshotter.refresh_live_state_statuses()
            unhealthy_symbols = [
                result
                for result in results
                if result.get("data_confidence") == "DATA_DEGRADED"
            ]
            market_snapshotter.update_runtime_state(
                cycle_status="healthy",
                symbol_results=results,
            )
            consecutive_failures = 0
            state["status"] = "healthy"
            state["consecutive_failures"] = consecutive_failures
            state["data_mode"] = "structured_only"
            state["symbols"] = results
            if unhealthy_symbols:
                state["degraded_symbols"] = [
                    {
                        "symbol": result.get("symbol"),
                        "status": result.get("status"),
                        "data_confidence": result.get("data_confidence"),
                        "last_error": result.get("last_error"),
                    }
                    for result in unhealthy_symbols
                ]
            state["last_cycle_finished_at"] = now_iso()
            save_state(state)
        except Exception as exc:
            stale_results = market_snapshotter.refresh_live_state_statuses()
            market_snapshotter.update_runtime_state(
                cycle_status="degraded",
                symbol_results=stale_results,
                last_error=f"{type(exc).__name__}: {exc}",
            )
            consecutive_failures += 1
            state["status"] = "degraded"
            state["data_mode"] = "structured_only"
            state["symbols"] = stale_results
            state["last_cycle_finished_at"] = now_iso()
            state["consecutive_failures"] = consecutive_failures
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            save_state(state)
            append_log(f"cycle failed: {type(exc).__name__}: {exc}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
