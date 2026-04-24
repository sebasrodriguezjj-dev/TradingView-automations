#!/usr/bin/env python3
"""
Local chart executor for the SMART MONEY - GOOD MONEY automation stack.

Purpose:
- Read the declarative desired chart state for automation-owned markings.
- Reconcile TradingView from that state using the local `tv` CLI.
- Keep chart writes outside Codex automations so modal/prompt failures do not
  block the analytical workflows themselves.

This executor intentionally preserves the strategy logic. It only changes the
delivery path for chart markings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from tv_gateway import TvGateway, now_iso, symbol_slug, timeframe_to_seconds


WORKSPACE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = WORKSPACE_DIR / "chart_runtime"
DESIRED_STATES_DIR = RUNTIME_DIR / "desired_states"
APPLIED_STATES_DIR = RUNTIME_DIR / "applied_states"
SCREENSHOTS_DIR = RUNTIME_DIR / "screenshots"
LOG_PATH = RUNTIME_DIR / "chart_executor.log"
HEALTH_PATH = RUNTIME_DIR / "chart_runtime_state.json"

OWNER_NAME = "SMART MONEY - GOOD MONEY Chart Runtime"
DEFAULT_TIMEFRAME = "5"
DEFAULT_INTERVAL_SECONDS = 10

SEMANTIC_COLORS = {
    "4H SUPPORT": "#089981",
    "4H RESISTANCE": "#F23645",
    "5M EXECUTION LONG": "#2157F3",
    "5M EXECUTION SHORT": "#FACC15",
    "ENTRY": "#2157F3",
    "SL": "#F23645",
    "TP1": "#089981",
    "TP2": "#089981",
    "TP3": "#089981",
    "PDH": "#F23645",
    "PDL": "#089981",
    "ON HIGH": "#FBBF24",
    "ON LOW": "#14B8A6",
    "RANGE HIGH": "#FBBF24",
    "RANGE LOW": "#14B8A6",
}

SHAPE_COUNT_EXPRESSION = """(() => {
  try {
    const chart = window.TradingViewApi &&
      window.TradingViewApi._activeChartWidgetWV &&
      window.TradingViewApi._activeChartWidgetWV.value &&
      window.TradingViewApi._activeChartWidgetWV.value();
    if (!chart || !chart.getAllShapes) return { ok: false, reason: "chart api unavailable" };
    return { ok: true, count: chart.getAllShapes().length };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
})()"""

CLEAR_ALL_SHAPES_EXPRESSION = """(() => {
  try {
    const chart = window.TradingViewApi &&
      window.TradingViewApi._activeChartWidgetWV &&
      window.TradingViewApi._activeChartWidgetWV.value &&
      window.TradingViewApi._activeChartWidgetWV.value();
    if (!chart || !chart.removeAllShapes || !chart.getAllShapes) {
      return { ok: false, reason: "chart api unavailable" };
    }
    chart.removeAllShapes();
    return { ok: true, count: chart.getAllShapes().length };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
})()"""

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


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def json_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def latest_bar_time() -> int:
    response = GATEWAY.run_tv(["ohlcv", "--count", "3"])
    bars = response.get("bars") or []
    if not bars:
        raise RuntimeError("Unable to resolve latest bar time from TradingView.")
    return int(bars[-1]["time"])


def fallback_clear_via_ui() -> bool:
    response = GATEWAY.try_tv(
        ["ui", "click", "--by", "aria-label", "--value", "Remove objects"],
        timeout=10,
    )
    if response and response.get("success"):
        time.sleep(0.8)
        GATEWAY.dismiss_modals()
        GATEWAY.try_tv(["ui", "keyboard", "Enter"], timeout=5)
        time.sleep(0.8)
        return True
    return False


def get_shape_count() -> int | None:
    response = GATEWAY.try_tv(["ui", "eval", SHAPE_COUNT_EXPRESSION], timeout=10)
    if not response or not response.get("success"):
        return None
    result = response.get("result") or {}
    if not result.get("ok"):
        return None
    count = result.get("count")
    return int(count) if isinstance(count, (int, float)) else None


def clear_all_shapes_via_ui_eval() -> bool:
    response = GATEWAY.try_tv(["ui", "eval", CLEAR_ALL_SHAPES_EXPRESSION], timeout=10)
    if not response or not response.get("success"):
        return False
    result = response.get("result") or {}
    if not result.get("ok"):
        return False
    count = result.get("count")
    return isinstance(count, (int, float)) and int(count) == 0


def clear_owned_shapes(symbol: str, timeframe: str) -> None:
    clear_error: Exception | None = None

    for _ in range(3):
        try:
            GATEWAY.wait_for_chart_ready(symbol, timeframe)
            if clear_all_shapes_via_ui_eval():
                return
            GATEWAY.run_tv(["draw", "clear"], timeout=20)
            time.sleep(0.6)
            remaining = get_shape_count()
            if remaining == 0:
                return
        except Exception as exc:
            clear_error = exc
        GATEWAY.dismiss_modals()
        time.sleep(1.5)

    if fallback_clear_via_ui():
        time.sleep(1.0)
        remaining = get_shape_count()
        if remaining == 0:
            return

    raise clear_error or RuntimeError("Unable to clear automation-owned shapes from the chart.")


def draw_horizontal_level(price: float, color: str, anchor_time: int) -> None:
    overrides = json.dumps({"linecolor": color, "linewidth": 1})
    GATEWAY.run_tv(
        [
            "draw",
            "shape",
            "--type",
            "horizontal_line",
            "--price",
            f"{price}",
            "--time",
            str(anchor_time),
            "--overrides",
            overrides,
        ],
        timeout=15,
    )


def draw_finite_level(price: float, color: str, start_time: int, end_time: int) -> None:
    overrides = json.dumps({"linecolor": color, "linewidth": 1})
    GATEWAY.run_tv(
        [
            "draw",
            "shape",
            "--type",
            "trend_line",
            "--price",
            f"{price}",
            "--time",
            str(start_time),
            "--price2",
            f"{price}",
            "--time2",
            str(end_time),
            "--overrides",
            overrides,
        ],
        timeout=15,
    )


def draw_text_label(price: float, label: str, color: str, label_time: int) -> None:
    overrides = json.dumps(
        {
            "color": color,
            "fontsize": 14,
            "fillBackground": False,
            "drawBorder": False,
        }
    )
    GATEWAY.run_tv(
        [
            "draw",
            "shape",
            "--type",
            "text",
            "--price",
            f"{price}",
            "--time",
            str(label_time),
            "--text",
            label,
            "--overrides",
            overrides,
        ],
        timeout=15,
    )


def render_level_set(state: dict[str, Any], latest_time: int, dry_run: bool) -> list[str]:
    timeframe = state.get("timeframe", DEFAULT_TIMEFRAME)
    tf_seconds = timeframe_to_seconds(str(timeframe))
    finite_start = latest_time - tf_seconds
    finite_end = latest_time + (4 * tf_seconds)
    finite_label_time = latest_time + (5 * tf_seconds)
    htf_label_time = latest_time + (5 * tf_seconds)
    rendered: list[str] = []

    levels = state.get("levels") or {}
    ordered_groups = [
        ("htf", "infinite"),
        ("execution_5m", "finite"),
        ("trade_entry", "finite"),
    ]

    for group_name, default_style in ordered_groups:
        for raw_level in levels.get(group_name, []):
            if raw_level is None or raw_level.get("enabled", True) is False:
                continue

            label = str(raw_level["label"])
            price = float(raw_level["price"])
            semantic = str(raw_level.get("semantic", label))
            style = str(raw_level.get("style", default_style)).lower()
            color = str(raw_level.get("color") or SEMANTIC_COLORS.get(semantic, "#2157F3"))
            rendered.append(label)

            if dry_run:
                continue

            if style == "infinite":
                draw_horizontal_level(price=price, color=color, anchor_time=latest_time)
                draw_text_label(price=price, label=label, color=color, label_time=htf_label_time)
            else:
                draw_finite_level(
                    price=price,
                    color=color,
                    start_time=finite_start,
                    end_time=finite_end,
                )
                draw_text_label(price=price, label=label, color=color, label_time=finite_label_time)

    return rendered


def verify_screenshot(symbol: str) -> str | None:
    slug = symbol_slug(symbol).lower()
    output_name = f"{slug}-latest"
    response = GATEWAY.run_tv(
        ["screenshot", "--region", "chart", "--output", output_name],
        timeout=20,
        cwd=SCREENSHOTS_DIR,
    )
    path = response.get("path")
    if path:
        return str(path)
    candidate = SCREENSHOTS_DIR / f"{output_name}.png"
    return str(candidate) if candidate.exists() else None


def clear_and_redraw_owned_state(state: dict[str, Any], dry_run: bool) -> list[str]:
    symbol = str(state["symbol"])
    timeframe = str(state.get("timeframe", DEFAULT_TIMEFRAME))
    GATEWAY.ensure_symbol_and_timeframe(symbol, timeframe)
    GATEWAY.dismiss_modals()

    latest_time = latest_bar_time()
    if not dry_run:
        clear_owned_shapes(symbol, timeframe)
        time.sleep(0.4)
        latest_time = latest_bar_time()

    return render_level_set(state, latest_time=latest_time, dry_run=dry_run)


def applied_state_path(symbol: str) -> Path:
    return APPLIED_STATES_DIR / f"{symbol_slug(symbol)}.json"


def load_desired_states(symbol_filter: str | None = None) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for path in sorted(DESIRED_STATES_DIR.glob("*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            append_log(f"skip invalid desired state file: {path.name}")
            continue
        symbol = str(payload.get("symbol", ""))
        if symbol_filter and symbol_filter != symbol and symbol_filter != symbol_slug(symbol):
            continue
        payload["_path"] = str(path)
        states.append(payload)
    return states


def update_health(symbol: str, status: str, **fields: Any) -> None:
    health = load_json(HEALTH_PATH, default={}) or {}
    health.setdefault("owner", OWNER_NAME)
    health["last_updated_at"] = now_iso()
    health.setdefault("symbols", {})
    health["symbols"].setdefault(symbol, {})
    symbol_state = health["symbols"][symbol]
    symbol_state["status"] = status
    for key, value in fields.items():
        if value is None:
            symbol_state.pop(key, None)
        else:
            symbol_state[key] = value
    save_json(HEALTH_PATH, health)


def reconcile_symbol(state: dict[str, Any], force: bool = False, dry_run: bool = False) -> dict[str, Any]:
    symbol = str(state["symbol"])
    state_hash = json_sha256(state)
    applied_path = applied_state_path(symbol)
    applied = load_json(applied_path, default={}) or {}

    if not force and applied.get("desired_hash") == state_hash:
        update_health(symbol, "noop", desired_hash=state_hash, last_noop_at=now_iso())
        return {
            "symbol": symbol,
            "status": "noop",
            "reason": "desired state unchanged",
        }

    update_health(symbol, "applying", desired_hash=state_hash, last_apply_started_at=now_iso())

    try:
        with GATEWAY.locked_session(timeout_seconds=180):
            GATEWAY.ensure_connection()
            rendered = clear_and_redraw_owned_state(state, dry_run=dry_run)
            screenshot_path = None if dry_run else verify_screenshot(symbol)

        result = {
            "owner": OWNER_NAME,
            "symbol": symbol,
            "desired_hash": state_hash,
            "desired_state_version": state.get("state_version"),
            "applied_at": now_iso(),
            "rendered_labels": rendered,
            "screenshot": screenshot_path,
            "dry_run": dry_run,
            "source_workflow": state.get("source_workflow"),
            "cleanup_scope": state.get("cleanup_scope"),
        }
        if not dry_run:
            save_json(applied_path, result)
        update_health(
            symbol,
            "verified" if not dry_run else "dry-run",
            desired_hash=state_hash,
            last_success_at=now_iso(),
            screenshot=screenshot_path,
            rendered_labels=rendered,
            last_error=None,
            last_failed_at=None,
        )
        append_log(f"{symbol} applied ({'dry-run' if dry_run else 'live'}): {', '.join(rendered)}")
        return {"symbol": symbol, "status": "applied", "rendered": rendered, "screenshot": screenshot_path}
    except Exception as exc:
        GATEWAY.dismiss_modals()
        update_health(symbol, "failed", last_error=str(exc), last_failed_at=now_iso())
        append_log(f"{symbol} failed: {type(exc).__name__}: {exc}")
        raise


def reconcile_all(symbol_filter: str | None = None, force: bool = False, dry_run: bool = False) -> list[dict[str, Any]]:
    states = load_desired_states(symbol_filter=symbol_filter)
    results: list[dict[str, Any]] = []
    for state in states:
        results.append(reconcile_symbol(state, force=force, dry_run=dry_run))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile TradingView with desired chart states.")
    parser.add_argument("--watch", action="store_true", help="Poll desired state files continuously.")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS, help="Polling interval in seconds.")
    parser.add_argument("--symbol", help="Optional exact symbol filter, e.g. PEPPERSTONE:XAUUSD.")
    parser.add_argument("--force", action="store_true", help="Apply even if desired state hash is unchanged.")
    parser.add_argument("--dry-run", action="store_true", help="Compute what would be applied without touching the chart.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    append_log("executor started")

    def run_cycle() -> None:
        results = reconcile_all(symbol_filter=args.symbol, force=args.force, dry_run=args.dry_run)
        if not results:
            append_log("no desired states found")

    if args.watch:
        while True:
            try:
                run_cycle()
            except Exception as exc:
                append_log(f"watch cycle failed: {type(exc).__name__}: {exc}")
            time.sleep(max(1, int(args.interval)))
        return 0

    run_cycle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
