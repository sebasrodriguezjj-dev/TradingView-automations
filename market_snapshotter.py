#!/usr/bin/env python3
"""
Local market snapshotter for the SMART MONEY - GOOD MONEY automation stack.

Purpose:
- Be the only live market reader that talks to TradingView directly.
- Produce fresh local snapshots plus screenshots for XAUUSD and US30.
- Keep Codex automations off the direct TradingView read path so they do not
  block on MCP approval prompts.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from tv_gateway import TvGateway, now_iso, symbol_slug


WORKSPACE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = WORKSPACE_DIR / "market_runtime"
SNAPSHOTS_DIR = RUNTIME_DIR / "snapshots"
SCREENSHOTS_DIR = RUNTIME_DIR / "screenshots"
STATE_PATH = RUNTIME_DIR / "market_runtime_state.json"
LOG_PATH = RUNTIME_DIR / "market_snapshotter.log"

OWNER_NAME = "SMART MONEY - GOOD MONEY Market Runtime"
DEFAULT_FRESHNESS_SECONDS = 30
DEFAULT_OHLCV_COUNT = 120
CONTEXT_SCREENSHOT_STALE_SECONDS = 300

SYMBOLS = [
    "PEPPERSTONE:XAUUSD",
    "FOREXCOM:US30",
]

TIMEFRAMES = [
    ("D", "D"),
    ("240", "4H"),
    ("30", "30m"),
    ("15", "15m"),
    ("5", "5m"),
]

ALWAYS_SCREENSHOT_KEYS = {"5m"}
CONTEXT_SCREENSHOT_KEYS = {"4H", "30m", "15m"}

GATEWAY = TvGateway(owner_name=OWNER_NAME, log_path=LOG_PATH, workspace_dir=WORKSPACE_DIR)


def append_log(message: str) -> None:
    GATEWAY.append_log(message)


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def snapshot_path(symbol: str) -> Path:
    return SNAPSHOTS_DIR / f"{symbol_slug(symbol)}.json"


def now_local() -> datetime:
    return datetime.now().astimezone()


def iso_after(seconds: int) -> str:
    return (now_local() + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def screenshot_output_name(symbol: str, timeframe_label: str) -> str:
    safe_symbol = symbol_slug(symbol).lower()
    safe_tf = timeframe_label.lower().replace("m", "m").replace("h", "h")
    return f"{safe_symbol}-{safe_tf}-latest"


def screenshot_is_stale(screenshot_entry: dict[str, Any] | None, stale_seconds: int) -> bool:
    if not screenshot_entry:
        return True
    captured_at = screenshot_entry.get("captured_at")
    try:
        age = now_local() - datetime.fromisoformat(str(captured_at))
    except Exception:
        return True
    return age.total_seconds() >= stale_seconds


def capture_chart_screenshot(symbol: str, timeframe_label: str) -> dict[str, Any]:
    output_name = screenshot_output_name(symbol, timeframe_label)
    response = GATEWAY.run_tv(
        ["screenshot", "--region", "chart", "--output", output_name],
        timeout=20,
        cwd=SCREENSHOTS_DIR,
    )
    path = response.get("path")
    candidate = SCREENSHOTS_DIR / f"{output_name}.png"
    resolved_path = str(path) if path else str(candidate)
    return {
        "path": resolved_path,
        "captured_at": now_iso(),
        "timeframe": timeframe_label,
    }


def build_snapshot_payload(
    symbol: str,
    previous: dict[str, Any] | None,
    info_payload: dict[str, Any] | None,
    quote_payload: dict[str, Any] | None,
    timeframes: dict[str, Any],
    screenshots: dict[str, Any],
) -> dict[str, Any]:
    state_version = int(previous.get("state_version", 0)) + 1 if previous else 1
    as_of = now_iso()
    return {
        "version": 1,
        "owned_by": "smart-money-good-money-market-runtime",
        "state_version": state_version,
        "updated_at": as_of,
        "updated_by": "market_snapshotter",
        "source_runtime": OWNER_NAME,
        "symbol": symbol,
        "status": "fresh",
        "as_of": as_of,
        "fresh_until": iso_after(DEFAULT_FRESHNESS_SECONDS),
        "freshness_seconds": DEFAULT_FRESHNESS_SECONDS,
        "visual_mode": "data + screenshots",
        "timeframes_captured": list(timeframes.keys()),
        "screenshots": screenshots,
        "market": {
            "info": info_payload or {},
            "quote": quote_payload or {},
        },
        "timeframes": timeframes,
        "last_error": None,
    }


def build_degraded_payload(symbol: str, previous: dict[str, Any] | None, error: Exception) -> dict[str, Any]:
    payload = dict(previous or {})
    payload.setdefault("version", 1)
    payload.setdefault("owned_by", "smart-money-good-money-market-runtime")
    payload.setdefault("state_version", 0)
    payload["state_version"] = int(payload["state_version"]) + 1
    payload["updated_at"] = now_iso()
    payload["updated_by"] = "market_snapshotter"
    payload["source_runtime"] = OWNER_NAME
    payload["symbol"] = symbol
    payload["status"] = "degraded"
    payload["last_error"] = f"{type(error).__name__}: {error}"
    payload.setdefault("as_of", now_iso())
    payload.setdefault("fresh_until", payload["as_of"])
    payload.setdefault("freshness_seconds", DEFAULT_FRESHNESS_SECONDS)
    payload.setdefault("visual_mode", "data + screenshots")
    payload.setdefault("screenshots", {})
    payload.setdefault("market", {})
    payload.setdefault("timeframes", {})
    return payload


def refresh_snapshot_statuses() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    current = now_local()

    for path in sorted(SNAPSHOTS_DIR.glob("*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue

        previous_status = str(payload.get("status", "unknown"))
        last_error = payload.get("last_error")
        fresh_until_raw = payload.get("fresh_until")
        next_status = previous_status

        try:
            fresh_until = datetime.fromisoformat(str(fresh_until_raw))
            is_stale = current > fresh_until
        except Exception:
            is_stale = True

        if previous_status != "degraded":
            next_status = "stale" if is_stale else "fresh"
        elif not last_error and not is_stale:
            next_status = "fresh"

        if next_status != previous_status:
            payload["status"] = next_status
            payload["updated_at"] = now_iso()
            save_json(path, payload)

        results.append(
            {
                "symbol": payload.get("symbol"),
                "status": payload.get("status"),
                "fresh_until": payload.get("fresh_until"),
            }
        )

    return results


def capture_symbol(symbol: str, dry_run: bool = False) -> dict[str, Any]:
    path = snapshot_path(symbol)
    previous = load_json(path, default={}) or {}

    with GATEWAY.locked_session(timeout_seconds=240):
        GATEWAY.ensure_connection()
        original_status = GATEWAY.run_tv(["status"], timeout=10)
        info_payload: dict[str, Any] | None = None
        quote_payload: dict[str, Any] | None = None
        timeframes: dict[str, Any] = {}
        screenshots: dict[str, Any] = dict(previous.get("screenshots") or {})

        try:
            for timeframe_value, timeframe_label in TIMEFRAMES:
                GATEWAY.ensure_symbol_and_timeframe(symbol, timeframe_value)
                state_payload = GATEWAY.run_tv(["state"], timeout=10)
                ohlcv_payload = GATEWAY.run_tv(
                    ["ohlcv", "--count", str(DEFAULT_OHLCV_COUNT)],
                    timeout=20,
                )
                bars = ohlcv_payload.get("bars") or []
                quote_payload = quote_payload or GATEWAY.try_tv(["quote"], timeout=10)
                info_payload = info_payload or GATEWAY.try_tv(["info"], timeout=10)

                timeframes[timeframe_label] = {
                    "timeframe": timeframe_value,
                    "captured_at": now_iso(),
                    "state": state_payload,
                    "bars": bars,
                    "bar_count": len(bars),
                    "latest_bar_time": bars[-1]["time"] if bars else None,
                }

                if timeframe_label in ALWAYS_SCREENSHOT_KEYS or (
                    timeframe_label in CONTEXT_SCREENSHOT_KEYS
                    and screenshot_is_stale(
                        screenshots.get(timeframe_label),
                        stale_seconds=CONTEXT_SCREENSHOT_STALE_SECONDS,
                    )
                ):
                    screenshots[timeframe_label] = capture_chart_screenshot(symbol, timeframe_label)

            payload = build_snapshot_payload(
                symbol=symbol,
                previous=previous,
                info_payload=info_payload,
                quote_payload=quote_payload,
                timeframes=timeframes,
                screenshots=screenshots,
            )
        except Exception as exc:
            payload = build_degraded_payload(symbol=symbol, previous=previous, error=exc)
            if not dry_run:
                save_json(path, payload)
            append_log(f"{symbol} snapshot failed: {type(exc).__name__}: {exc}")
            raise
        finally:
            original_symbol = original_status.get("chart_symbol")
            original_resolution = original_status.get("chart_resolution")
            if original_symbol and original_resolution:
                try:
                    GATEWAY.ensure_symbol_and_timeframe(str(original_symbol), str(original_resolution))
                except Exception as restore_exc:
                    append_log(
                        f"restore view failed after snapshot cycle for {symbol}: "
                        f"{type(restore_exc).__name__}: {restore_exc}"
                    )
            GATEWAY.dismiss_modals()

    if not dry_run:
        save_json(path, payload)
    append_log(f"{symbol} snapshot captured ({'dry-run' if dry_run else 'live'})")
    return payload


def update_runtime_state(cycle_status: str, symbol_results: list[dict[str, Any]], last_error: str | None = None) -> None:
    payload = {
        "owner": OWNER_NAME,
        "updated_at": now_iso(),
        "status": cycle_status,
        "freshness_seconds": DEFAULT_FRESHNESS_SECONDS,
        "symbols": symbol_results,
    }
    if last_error:
        payload["last_error"] = last_error
    save_json(STATE_PATH, payload)


def capture_all(symbol_filter: str | None = None, dry_run: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for symbol in SYMBOLS:
        if symbol_filter and symbol_filter != symbol and symbol_filter != symbol_slug(symbol):
            continue
        try:
            payload = capture_symbol(symbol, dry_run=dry_run)
            results.append(
                {
                    "symbol": symbol,
                    "status": payload.get("status"),
                    "as_of": payload.get("as_of"),
                    "fresh_until": payload.get("fresh_until"),
                }
            )
        except Exception as exc:
            failures.append(f"{symbol}: {type(exc).__name__}: {exc}")
            degraded = load_json(snapshot_path(symbol), default={}) or {}
            results.append(
                {
                    "symbol": symbol,
                    "status": degraded.get("status", "degraded"),
                    "as_of": degraded.get("as_of"),
                    "fresh_until": degraded.get("fresh_until"),
                    "last_error": degraded.get("last_error"),
                }
            )
    if failures:
        raise RuntimeError(" | ".join(failures))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture live TradingView market snapshots for automations.")
    parser.add_argument("--watch", action="store_true", help="Poll continuously instead of running one capture cycle.")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval in seconds.")
    parser.add_argument("--symbol", help="Optional exact symbol filter, e.g. PEPPERSTONE:XAUUSD.")
    parser.add_argument("--dry-run", action="store_true", help="Read live data without writing snapshot files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    append_log("snapshotter started")

    def run_cycle() -> None:
        refresh_snapshot_statuses()
        results = capture_all(symbol_filter=args.symbol, dry_run=args.dry_run)
        update_runtime_state(
            cycle_status="dry-run" if args.dry_run else "healthy",
            symbol_results=results,
        )

    if args.watch:
        while True:
            try:
                run_cycle()
            except Exception as exc:
                refresh_snapshot_statuses()
                update_runtime_state(
                    cycle_status="degraded",
                    symbol_results=refresh_snapshot_statuses(),
                    last_error=f"{type(exc).__name__}: {exc}",
                )
                append_log(f"watch cycle failed: {type(exc).__name__}: {exc}")

            time.sleep(max(1, int(args.interval)))
        return 0

    run_cycle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
