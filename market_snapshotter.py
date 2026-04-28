#!/usr/bin/env python3
"""
TradingView structured live-state reader for the SMART MONEY - GOOD MONEY stack.

Purpose:
- Be the only live market reader that talks to TradingView directly.
- Produce fresh structured live-state JSON for XAUUSD and US30.
- Preserve a deprecated structured-only mirror under snapshots during transition.
- Keep Codex automations off the direct TradingView read path so they do not
  block on MCP approval prompts.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tv_gateway import TvGateway, now_iso, symbol_slug


WORKSPACE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = WORKSPACE_DIR / "market_runtime"
LIVE_STATE_DIR = RUNTIME_DIR / "live_state"
SNAPSHOTS_DIR = RUNTIME_DIR / "snapshots"
SCREENSHOTS_DIR = RUNTIME_DIR / "screenshots"
STATE_PATH = RUNTIME_DIR / "market_runtime_state.json"
LOG_PATH = RUNTIME_DIR / "market_snapshotter.log"

OWNER_NAME = "SMART MONEY - GOOD MONEY Market Runtime"
LIVE_STATE_OWNER = "smart-money-good-money-tradingview-live-state"
LIVE_STATE_READER = "tradingview_live_state_reader"
DEFAULT_FRESHNESS_SECONDS = 30
DEFAULT_OHLCV_COUNT = 120
def load_new_york_tz() -> timezone | ZoneInfo:
    try:
        return ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        # Windows images in this workspace do not always ship tzdata.
        # Use the current EDT offset as a deterministic fallback so the live
        # reader can still classify session context instead of failing at
        # import-time. This does not change strategy logic; it keeps the
        # runtime alive until full tzdata is available again.
        return timezone(timedelta(hours=-4), name="America/New_York_fallback")


NY_TZ = load_new_york_tz()
REQUIRED_TIMEFRAMES = {"D", "4H", "30m", "15m", "5m"}
PIVOT_LEFT = 2
PIVOT_RIGHT = 2
EQUAL_LEVEL_TOLERANCE_RATIO = 0.0002

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


def live_state_path(symbol: str) -> Path:
    return LIVE_STATE_DIR / f"{symbol_slug(symbol)}.json"


def snapshot_path(symbol: str) -> Path:
    return SNAPSHOTS_DIR / f"{symbol_slug(symbol)}.json"


def now_local() -> datetime:
    return datetime.now().astimezone()


def iso_after(seconds: int) -> str:
    return (now_local() + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def timestamp_to_dt(timestamp_value: Any, tz: timezone | ZoneInfo = timezone.utc) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(timestamp_value), tz=timezone.utc).astimezone(tz)
    except Exception:
        return None


def value_or_none(value: Any) -> Any:
    return value if value is not None else None


def bar_range(bar: dict[str, Any]) -> float | None:
    high = safe_float(bar.get("high"))
    low = safe_float(bar.get("low"))
    if high is None or low is None:
        return None
    return max(0.0, high - low)


def bar_body(bar: dict[str, Any]) -> float | None:
    open_price = safe_float(bar.get("open"))
    close_price = safe_float(bar.get("close"))
    if open_price is None or close_price is None:
        return None
    return abs(close_price - open_price)


def latest_price(quote_payload: dict[str, Any] | None) -> float | None:
    if not isinstance(quote_payload, dict):
        return None
    for key in ("last", "close", "price"):
        price = safe_float(quote_payload.get(key))
        if price is not None:
            return price
    return None


def price_tolerance(last_price: float | None) -> float:
    if last_price is None:
        return 0.0
    return abs(last_price) * EQUAL_LEVEL_TOLERANCE_RATIO


def timeframe_payload(timeframes: dict[str, Any], label: str) -> dict[str, Any]:
    payload = timeframes.get(label)
    return payload if isinstance(payload, dict) else {}


def bars_for_timeframe(timeframes: dict[str, Any], label: str) -> list[dict[str, Any]]:
    payload = timeframe_payload(timeframes, label)
    bars = payload.get("bars")
    return bars if isinstance(bars, list) else []


def build_empty_derived_features() -> dict[str, Any]:
    return {
        "liquidity": {
            "nearest_buy_side": None,
            "nearest_sell_side": None,
            "recent_swing_highs": [],
            "recent_swing_lows": [],
            "equal_highs": [],
            "equal_lows": [],
            "pdh": None,
            "pdl": None,
            "session_high": None,
            "session_low": None,
            "liquidity_state": "unknown",
        },
        "reaction_zones": {
            "supply": [],
            "demand": [],
            "flip_zones": [],
            "displacement_origins": [],
        },
        "volume_support": {
            "available": False,
            "volume_field_detected": None,
            "is_tick_volume": None,
            "usable_for_vpa": False,
        },
        "price_action": {
            "last_closed_5m_bar": None,
            "current_5m_bar": None,
            "recent_retests": [],
            "failed_retests": [],
            "reclaims": [],
            "rejections": [],
            "micro_structure": "unknown",
        },
        "session_context": {
            "session": "unknown",
            "opening_range": {
                "high": None,
                "low": None,
                "start": None,
                "end": None,
                "status": "unknown",
            },
            "ny_first_impulse": {
                "direction": "unknown",
                "liquidity_paid": False,
                "chase_risk": False,
            },
        },
        "risk_inputs": {
            "unit": "unknown",
            "preferred_stop_min": 60,
            "preferred_stop_max": 80,
            "hard_max": 100,
            "tp1": 60,
            "tp2": 80,
            "tp3": 100,
            "candidate_entry": None,
            "candidate_invalidation": None,
            "risk_required": None,
            "risk_permission": "unknown",
        },
        "timing_context": {
            "previous_timing_state": None,
            "current_timing_state": "unknown",
            "liquidity_already_paid": False,
            "first_target_already_hit": False,
            "chase_risk": False,
            "recommended_discipline": "unknown",
        },
    }


def validate_structured_data(
    quote_payload: dict[str, Any] | None,
    timeframes: dict[str, Any],
) -> dict[str, Any]:
    missing_fields: list[str] = []

    if not quote_payload:
        missing_fields.append("market.quote")

    for tf in REQUIRED_TIMEFRAMES:
        tf_payload = timeframes.get(tf)
        if not tf_payload:
            missing_fields.append(f"timeframes.{tf}")
            continue
        if not tf_payload.get("bars"):
            missing_fields.append(f"timeframes.{tf}.bars")
        if not tf_payload.get("latest_bar_time"):
            missing_fields.append(f"timeframes.{tf}.latest_bar_time")

    if missing_fields:
        return {
            "status": "DATA_DEGRADED",
            "decision_allowed": False,
            "missing_fields": missing_fields,
        }

    return {
        "status": "FULL_DATA",
        "decision_allowed": True,
        "missing_fields": [],
    }


def find_pivots(
    bars: list[dict[str, Any]],
    side: str,
    left: int = PIVOT_LEFT,
    right: int = PIVOT_RIGHT,
) -> list[dict[str, Any]]:
    pivots: list[dict[str, Any]] = []
    if len(bars) < left + right + 1:
        return pivots

    key = "high" if side == "high" else "low"
    for index in range(left, len(bars) - right):
        center = safe_float(bars[index].get(key))
        if center is None:
            continue
        left_values = [safe_float(bar.get(key)) for bar in bars[index - left : index]]
        right_values = [safe_float(bar.get(key)) for bar in bars[index + 1 : index + 1 + right]]
        if any(value is None for value in left_values + right_values):
            continue
        if side == "high":
            is_pivot = all(center > value for value in left_values + right_values)
        else:
            is_pivot = all(center < value for value in left_values + right_values)
        if not is_pivot:
            continue
        pivots.append(
            {
                "price": center,
                "time": bars[index].get("time"),
            }
        )
    return pivots


def find_equal_levels(swings: list[dict[str, Any]], tolerance: float) -> list[dict[str, Any]]:
    equal_levels: list[dict[str, Any]] = []
    if tolerance <= 0 or len(swings) < 2:
        return equal_levels

    recent_swings = swings[-8:]
    for index in range(len(recent_swings) - 1):
        first = recent_swings[index]
        second = recent_swings[index + 1]
        first_price = safe_float(first.get("price"))
        second_price = safe_float(second.get("price"))
        if first_price is None or second_price is None:
            continue
        if abs(first_price - second_price) <= tolerance:
            equal_levels.append(
                {
                    "price": round((first_price + second_price) / 2, 5),
                    "times": [first.get("time"), second.get("time")],
                }
            )
    return equal_levels


def classify_session(now_ny: datetime) -> tuple[str, datetime | None]:
    minutes = now_ny.hour * 60 + now_ny.minute

    if minutes >= (19 * 60 + 30) or minutes <= 59:
        start_date = now_ny.date() if minutes >= (19 * 60 + 30) else (now_ny - timedelta(days=1)).date()
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=NY_TZ).replace(hour=19, minute=30)
        return "ASIA", start_dt

    if 7 * 60 + 30 <= minutes <= 8 * 60 + 29:
        return "NY_OPEN", now_ny.replace(hour=7, minute=30, second=0, microsecond=0)

    if 8 * 60 + 30 <= minutes <= 10 * 60 + 29:
        return "POST_OPEN", now_ny.replace(hour=8, minute=30, second=0, microsecond=0)

    if 10 * 60 + 30 <= minutes <= 15 * 60 + 29:
        return "MID_SESSION", now_ny.replace(hour=10, minute=30, second=0, microsecond=0)

    if 15 * 60 + 30 <= minutes <= 18 * 60 + 29:
        return "EOD", now_ny.replace(hour=15, minute=30, second=0, microsecond=0)

    return "unknown", None


def bars_between(
    bars: list[dict[str, Any]],
    start_dt: datetime | None,
    end_dt: datetime | None,
    tz: ZoneInfo = NY_TZ,
) -> list[dict[str, Any]]:
    if start_dt is None or end_dt is None:
        return []
    selected: list[dict[str, Any]] = []
    for bar in bars:
        bar_dt = timestamp_to_dt(bar.get("time"), tz=tz)
        if bar_dt is None:
            continue
        if start_dt <= bar_dt <= end_dt:
            selected.append(bar)
    return selected


def derive_liquidity(
    timeframes: dict[str, Any],
    quote_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    result = build_empty_derived_features()["liquidity"]
    last_price = latest_price(quote_payload)
    tolerance = price_tolerance(last_price)

    bars_5m = bars_for_timeframe(timeframes, "5m")
    bars_source = bars_5m if len(bars_5m) >= 12 else bars_for_timeframe(timeframes, "15m")
    highs = find_pivots(bars_source, "high")
    lows = find_pivots(bars_source, "low")

    result["recent_swing_highs"] = highs[-6:]
    result["recent_swing_lows"] = lows[-6:]
    result["equal_highs"] = find_equal_levels(highs, tolerance)
    result["equal_lows"] = find_equal_levels(lows, tolerance)

    if last_price is not None:
        above = [pivot for pivot in highs if safe_float(pivot.get("price")) is not None and safe_float(pivot.get("price")) > last_price]
        below = [pivot for pivot in lows if safe_float(pivot.get("price")) is not None and safe_float(pivot.get("price")) < last_price]
        if above:
            result["nearest_buy_side"] = min(above, key=lambda item: safe_float(item.get("price")) or float("inf"))
        if below:
            result["nearest_sell_side"] = max(below, key=lambda item: safe_float(item.get("price")) or float("-inf"))

    daily_bars = bars_for_timeframe(timeframes, "D")
    if len(daily_bars) >= 2:
        previous_day = daily_bars[-2]
        result["pdh"] = safe_float(previous_day.get("high"))
        result["pdl"] = safe_float(previous_day.get("low"))

    now_ny = now_local().astimezone(NY_TZ)
    _, session_start = classify_session(now_ny)
    session_bars = bars_between(bars_5m, session_start, now_ny, tz=NY_TZ)
    if session_bars:
        highs_in_session = [safe_float(bar.get("high")) for bar in session_bars]
        lows_in_session = [safe_float(bar.get("low")) for bar in session_bars]
        highs_clean = [value for value in highs_in_session if value is not None]
        lows_clean = [value for value in lows_in_session if value is not None]
        result["session_high"] = max(highs_clean) if highs_clean else None
        result["session_low"] = min(lows_clean) if lows_clean else None

    last_closed_bar = bars_5m[-1] if bars_5m else None
    recent_bars = bars_5m[-3:] if len(bars_5m) >= 3 else bars_5m
    if last_price is None or not last_closed_bar:
        return result

    candidates: list[tuple[str, float]] = []
    if isinstance(result["nearest_buy_side"], dict):
        level = safe_float(result["nearest_buy_side"].get("price"))
        if level is not None:
            candidates.append(("buy", level))
    if isinstance(result["nearest_sell_side"], dict):
        level = safe_float(result["nearest_sell_side"].get("price"))
        if level is not None:
            candidates.append(("sell", level))

    if not candidates:
        return result

    chosen_side, chosen_level = min(candidates, key=lambda item: abs(item[1] - last_price))
    recent_high = max((safe_float(bar.get("high")) or float("-inf")) for bar in recent_bars)
    recent_low = min((safe_float(bar.get("low")) or float("inf")) for bar in recent_bars)
    last_close = safe_float(last_closed_bar.get("close"))

    if chosen_side == "buy" and recent_high > chosen_level + tolerance and last_close is not None:
        if last_close < chosen_level - tolerance:
            result["liquidity_state"] = "rejected"
        elif last_close > chosen_level + tolerance:
            result["liquidity_state"] = "already_paid" if last_price > chosen_level + (2 * tolerance) else "reclaimed"
        else:
            result["liquidity_state"] = "swept"
        return result

    if chosen_side == "sell" and recent_low < chosen_level - tolerance and last_close is not None:
        if last_close > chosen_level + tolerance:
            result["liquidity_state"] = "rejected"
        elif last_close < chosen_level - tolerance:
            result["liquidity_state"] = "already_paid" if last_price < chosen_level - (2 * tolerance) else "reclaimed"
        else:
            result["liquidity_state"] = "swept"
        return result

    result["liquidity_state"] = "targeting"
    return result


def displacement_zone_from_bar(
    bar: dict[str, Any],
    timeframe_label: str,
    zone_type: str,
    source_reason: str,
) -> dict[str, Any]:
    return {
        "timeframe": timeframe_label,
        "high": safe_float(bar.get("high")),
        "low": safe_float(bar.get("low")),
        "origin_time": bar.get("time"),
        "status": "fresh",
        "source_reason": source_reason,
        "zone_type": zone_type,
    }


def derive_reaction_zones(timeframes: dict[str, Any]) -> dict[str, Any]:
    result = build_empty_derived_features()["reaction_zones"]

    for timeframe_label in ("30m", "15m"):
        bars = bars_for_timeframe(timeframes, timeframe_label)
        if len(bars) < 25:
            continue

        for index in range(20, len(bars)):
            bar = bars[index]
            current_range = bar_range(bar)
            current_body = bar_body(bar)
            if current_range is None or current_body is None or current_range <= 0:
                continue

            prior_ranges = [bar_range(item) for item in bars[index - 20 : index]]
            valid_ranges = [value for value in prior_ranges if value is not None and value > 0]
            if len(valid_ranges) < 10:
                continue

            median_range = median(valid_ranges)
            if current_range < (1.5 * median_range) or current_body < (0.6 * current_range):
                continue

            prior_window = bars[max(0, index - 10) : index]
            prior_highs = [safe_float(item.get("high")) for item in prior_window]
            prior_lows = [safe_float(item.get("low")) for item in prior_window]
            valid_highs = [value for value in prior_highs if value is not None]
            valid_lows = [value for value in prior_lows if value is not None]
            if not valid_highs or not valid_lows:
                continue

            close_price = safe_float(bar.get("close"))
            open_price = safe_float(bar.get("open"))
            high_price = safe_float(bar.get("high"))
            low_price = safe_float(bar.get("low"))
            if None in (close_price, open_price, high_price, low_price):
                continue

            if close_price > open_price and high_price > max(valid_highs):
                zone = displacement_zone_from_bar(bar, timeframe_label, "demand", "bullish displacement")
                result["demand"].append(zone)
                result["displacement_origins"].append(zone)
            elif close_price < open_price and low_price < min(valid_lows):
                zone = displacement_zone_from_bar(bar, timeframe_label, "supply", "bearish displacement")
                result["supply"].append(zone)
                result["displacement_origins"].append(zone)

    result["supply"] = result["supply"][-5:]
    result["demand"] = result["demand"][-5:]
    result["displacement_origins"] = result["displacement_origins"][-8:]
    return result


def derive_volume_support(timeframes: dict[str, Any]) -> dict[str, Any]:
    result = build_empty_derived_features()["volume_support"]

    def volume_profile(label: str) -> tuple[bool, bool]:
        has_numeric = False
        has_positive = False
        for bar in bars_for_timeframe(timeframes, label)[-20:]:
            volume = safe_float(bar.get("volume"))
            if volume is None:
                continue
            has_numeric = True
            if volume > 0:
                has_positive = True
        return has_numeric, has_positive

    availability = {label: volume_profile(label) for label in REQUIRED_TIMEFRAMES}
    result["available"] = any(profile[0] for profile in availability.values())
    result["volume_field_detected"] = "volume" if result["available"] else None
    result["usable_for_vpa"] = all(availability.get(label, (False, False))[1] for label in ("5m", "15m", "30m"))
    result["is_tick_volume"] = None
    return result


def candidate_levels_from_features(
    liquidity: dict[str, Any],
    reaction_zones: dict[str, Any],
) -> list[dict[str, Any]]:
    levels: list[dict[str, Any]] = []

    def push(level: Any, label: str) -> None:
        price = safe_float(level)
        if price is None:
            return
        levels.append({"level": price, "label": label})

    nearest_buy = liquidity.get("nearest_buy_side")
    nearest_sell = liquidity.get("nearest_sell_side")
    if isinstance(nearest_buy, dict):
        push(nearest_buy.get("price"), "nearest_buy_side")
    if isinstance(nearest_sell, dict):
        push(nearest_sell.get("price"), "nearest_sell_side")

    for key in ("pdh", "pdl", "session_high", "session_low"):
        push(liquidity.get(key), key)

    for zone_key in ("supply", "demand", "displacement_origins"):
        for zone in reaction_zones.get(zone_key, [])[-3:]:
            if not isinstance(zone, dict):
                continue
            push(zone.get("high"), f"{zone_key}.high")
            push(zone.get("low"), f"{zone_key}.low")

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for item in levels:
        key = (item["label"], round(item["level"], 5))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def append_event_if_new(target: list[dict[str, Any]], event: dict[str, Any], seen: set[tuple[str, int, str]]) -> None:
    level = safe_float(event.get("level"))
    event_time = event.get("time")
    direction = str(event.get("direction"))
    if level is None or event_time is None:
        return
    key = (round(level, 5), int(event_time), direction)
    if key in seen:
        return
    seen.add(key)
    target.append(event)


def derive_micro_structure(bars: list[dict[str, Any]]) -> str:
    highs = find_pivots(bars, "high")
    lows = find_pivots(bars, "low")
    if len(highs) < 2 or len(lows) < 2:
        return "unknown"

    high_prev = safe_float(highs[-2].get("price"))
    high_last = safe_float(highs[-1].get("price"))
    low_prev = safe_float(lows[-2].get("price"))
    low_last = safe_float(lows[-1].get("price"))
    if None in (high_prev, high_last, low_prev, low_last):
        return "unknown"
    if high_last > high_prev and low_last > low_prev:
        return "HH/HL"
    if high_last < high_prev and low_last < low_prev:
        return "LH/LL"
    return "mixed"


def derive_price_action(
    timeframes: dict[str, Any],
    quote_payload: dict[str, Any] | None,
    liquidity: dict[str, Any],
    reaction_zones: dict[str, Any],
) -> dict[str, Any]:
    result = build_empty_derived_features()["price_action"]
    bars_5m = bars_for_timeframe(timeframes, "5m")
    if not bars_5m:
        return result

    result["last_closed_5m_bar"] = bars_5m[-1]
    result["current_5m_bar"] = None
    result["micro_structure"] = derive_micro_structure(bars_5m)

    tolerance = price_tolerance(latest_price(quote_payload))
    levels = candidate_levels_from_features(liquidity, reaction_zones)
    recent_bars = bars_5m[-8:]
    retest_seen: set[tuple[str, int, str]] = set()
    failed_seen: set[tuple[str, int, str]] = set()
    reclaim_seen: set[tuple[str, int, str]] = set()
    rejection_seen: set[tuple[str, int, str]] = set()

    for level_info in levels[:10]:
        level = safe_float(level_info.get("level"))
        label = str(level_info.get("label"))
        if level is None:
            continue

        for index in range(1, len(recent_bars)):
            previous_bar = recent_bars[index - 1]
            current_bar = recent_bars[index]
            open_price = safe_float(current_bar.get("open"))
            close_price = safe_float(current_bar.get("close"))
            high_price = safe_float(current_bar.get("high"))
            low_price = safe_float(current_bar.get("low"))
            previous_close = safe_float(previous_bar.get("close"))
            current_range = bar_range(current_bar) or 0.0
            if None in (open_price, close_price, high_price, low_price, previous_close):
                continue
            if not (low_price <= level <= high_price):
                continue

            timestamp_value = current_bar.get("time")
            upper_wick = high_price - max(open_price, close_price)
            lower_wick = min(open_price, close_price) - low_price

            if previous_close > level + tolerance and close_price > level + tolerance:
                append_event_if_new(
                    result["recent_retests"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "support_hold",
                        "timeframe": "5m",
                        "note": label,
                    },
                    retest_seen,
                )

            if previous_close < level - tolerance and close_price < level - tolerance:
                append_event_if_new(
                    result["recent_retests"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "resistance_hold",
                        "timeframe": "5m",
                        "note": label,
                    },
                    retest_seen,
                )

            if open_price < level - tolerance and close_price > level + tolerance:
                append_event_if_new(
                    result["reclaims"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "up",
                        "timeframe": "5m",
                        "note": label,
                    },
                    reclaim_seen,
                )

            if open_price > level + tolerance and close_price < level - tolerance:
                append_event_if_new(
                    result["reclaims"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "down",
                        "timeframe": "5m",
                        "note": label,
                    },
                    reclaim_seen,
                )

            if previous_close > level + tolerance and close_price < level - tolerance:
                append_event_if_new(
                    result["failed_retests"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "down",
                        "timeframe": "5m",
                        "note": label,
                    },
                    failed_seen,
                )

            if previous_close < level - tolerance and close_price > level + tolerance:
                append_event_if_new(
                    result["failed_retests"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "up",
                        "timeframe": "5m",
                        "note": label,
                    },
                    failed_seen,
                )

            if current_range > 0 and close_price < level - tolerance and upper_wick > (0.35 * current_range):
                append_event_if_new(
                    result["rejections"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "sell",
                        "timeframe": "5m",
                        "note": label,
                    },
                    rejection_seen,
                )

            if current_range > 0 and close_price > level + tolerance and lower_wick > (0.35 * current_range):
                append_event_if_new(
                    result["rejections"],
                    {
                        "level": level,
                        "time": timestamp_value,
                        "direction": "buy",
                        "timeframe": "5m",
                        "note": label,
                    },
                    rejection_seen,
                )

    result["recent_retests"] = result["recent_retests"][-8:]
    result["failed_retests"] = result["failed_retests"][-8:]
    result["reclaims"] = result["reclaims"][-8:]
    result["rejections"] = result["rejections"][-8:]
    return result


def derive_session_context(
    timeframes: dict[str, Any],
    quote_payload: dict[str, Any] | None,
    liquidity: dict[str, Any],
) -> dict[str, Any]:
    result = build_empty_derived_features()["session_context"]
    bars_5m = bars_for_timeframe(timeframes, "5m")
    now_ny = now_local().astimezone(NY_TZ)
    session_name, session_start = classify_session(now_ny)
    result["session"] = session_name

    or_start = now_ny.replace(hour=7, minute=30, second=0, microsecond=0)
    or_end = now_ny.replace(hour=8, minute=0, second=0, microsecond=0)
    opening_range_bars = bars_between(bars_5m, or_start, or_end, tz=NY_TZ)
    if opening_range_bars:
        highs = [safe_float(bar.get("high")) for bar in opening_range_bars]
        lows = [safe_float(bar.get("low")) for bar in opening_range_bars]
        valid_highs = [value for value in highs if value is not None]
        valid_lows = [value for value in lows if value is not None]
        or_high = max(valid_highs) if valid_highs else None
        or_low = min(valid_lows) if valid_lows else None
        result["opening_range"]["high"] = or_high
        result["opening_range"]["low"] = or_low
        result["opening_range"]["start"] = or_start.isoformat(timespec="seconds")
        result["opening_range"]["end"] = or_end.isoformat(timespec="seconds")

        last_price = latest_price(quote_payload)
        session_bars = bars_between(bars_5m, or_start, now_ny, tz=NY_TZ)
        session_high = max((safe_float(bar.get("high")) or float("-inf")) for bar in session_bars) if session_bars else None
        session_low = min((safe_float(bar.get("low")) or float("inf")) for bar in session_bars) if session_bars else None
        if last_price is not None and or_high is not None and or_low is not None:
            if last_price > or_high:
                result["opening_range"]["status"] = "breakout"
            elif last_price < or_low:
                result["opening_range"]["status"] = "breakdown"
            elif session_high is not None and session_high > or_high:
                result["opening_range"]["status"] = "failed_breakout" if session_name in {"POST_OPEN", "MID_SESSION"} else "swept"
            elif session_low is not None and session_low < or_low:
                result["opening_range"]["status"] = "swept"
            else:
                result["opening_range"]["status"] = "inside"

    ny_impulse_bars = bars_between(bars_5m, or_start, or_end, tz=NY_TZ)
    if ny_impulse_bars:
        first_open = safe_float(ny_impulse_bars[0].get("open"))
        last_close = safe_float(ny_impulse_bars[-1].get("close"))
        if first_open is not None and last_close is not None:
            if last_close > first_open:
                result["ny_first_impulse"]["direction"] = "up"
            elif last_close < first_open:
                result["ny_first_impulse"]["direction"] = "down"
            else:
                result["ny_first_impulse"]["direction"] = "mixed"

    liquidity_paid = liquidity.get("liquidity_state") == "already_paid"
    result["ny_first_impulse"]["liquidity_paid"] = liquidity_paid
    result["ny_first_impulse"]["chase_risk"] = bool(liquidity_paid and session_name in {"NY_OPEN", "POST_OPEN", "MID_SESSION"})
    return result


def derive_risk_inputs(symbol: str) -> dict[str, Any]:
    result = build_empty_derived_features()["risk_inputs"]
    if "XAUUSD" in symbol:
        result["unit"] = "pips"
    elif "US30" in symbol:
        result["unit"] = "points"
    return result


def derive_timing_context(
    liquidity: dict[str, Any],
    session_context: dict[str, Any],
) -> dict[str, Any]:
    result = build_empty_derived_features()["timing_context"]
    liquidity_state = str(liquidity.get("liquidity_state", "unknown"))
    liquidity_paid = liquidity_state == "already_paid"
    chase_risk = bool(liquidity_paid or session_context.get("ny_first_impulse", {}).get("chase_risk"))

    result["previous_timing_state"] = None
    result["liquidity_already_paid"] = liquidity_paid
    result["first_target_already_hit"] = liquidity_paid
    result["chase_risk"] = chase_risk

    if liquidity_paid and chase_risk:
        result["current_timing_state"] = "EXPIRED"
        result["recommended_discipline"] = "DO_NOT_CHASE"
    elif liquidity_paid:
        result["current_timing_state"] = "TRIGGERED"
        result["recommended_discipline"] = "WAIT_FOR_NEW_RETEST"
    else:
        result["current_timing_state"] = "unknown"
        result["recommended_discipline"] = "unknown"

    return result


def build_derived_features(
    symbol: str,
    timeframes: dict[str, Any],
    quote_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    derived = build_empty_derived_features()
    warnings: list[str] = []

    builders = {
        "liquidity": lambda: derive_liquidity(timeframes, quote_payload),
        "reaction_zones": lambda: derive_reaction_zones(timeframes),
        "volume_support": lambda: derive_volume_support(timeframes),
    }

    for key, builder in builders.items():
        try:
            derived[key] = builder()
        except Exception as exc:
            warnings.append(f"derived_features.{key}: {type(exc).__name__}: {exc}")

    try:
        derived["price_action"] = derive_price_action(
            timeframes,
            quote_payload,
            derived["liquidity"],
            derived["reaction_zones"],
        )
    except Exception as exc:
        warnings.append(f"derived_features.price_action: {type(exc).__name__}: {exc}")

    try:
        derived["session_context"] = derive_session_context(
            timeframes,
            quote_payload,
            derived["liquidity"],
        )
    except Exception as exc:
        warnings.append(f"derived_features.session_context: {type(exc).__name__}: {exc}")

    try:
        derived["risk_inputs"] = derive_risk_inputs(symbol)
    except Exception as exc:
        warnings.append(f"derived_features.risk_inputs: {type(exc).__name__}: {exc}")

    try:
        derived["timing_context"] = derive_timing_context(
            derived["liquidity"],
            derived["session_context"],
        )
    except Exception as exc:
        warnings.append(f"derived_features.timing_context: {type(exc).__name__}: {exc}")

    return derived, warnings


def derive_data_confidence(
    quote_payload: dict[str, Any] | None,
    timeframes: dict[str, Any],
    derived_warnings: list[str],
) -> dict[str, Any]:
    raw_validation = validate_structured_data(quote_payload, timeframes)
    if raw_validation["status"] == "DATA_DEGRADED":
        return raw_validation

    if derived_warnings:
        return {
            "status": "PARTIAL_DATA",
            "decision_allowed": True,
            "missing_fields": derived_warnings,
        }

    return raw_validation


def build_live_state_payload(
    symbol: str,
    previous: dict[str, Any] | None,
    info_payload: dict[str, Any] | None,
    quote_payload: dict[str, Any] | None,
    timeframes: dict[str, Any],
    derived_features: dict[str, Any],
    data_confidence: dict[str, Any],
) -> dict[str, Any]:
    state_version = int(previous.get("state_version", 0)) + 1 if previous else 1
    as_of = now_iso()
    payload_status = "degraded" if data_confidence.get("status") == "DATA_DEGRADED" else "fresh"

    return {
        "version": 2,
        "owned_by": LIVE_STATE_OWNER,
        "state_version": state_version,
        "updated_at": as_of,
        "updated_by": LIVE_STATE_READER,
        "source_runtime": OWNER_NAME,
        "source": "TradingView structured live state",
        "symbol": symbol,
        "status": payload_status,
        "as_of": as_of,
        "fresh_until": iso_after(DEFAULT_FRESHNESS_SECONDS),
        "freshness_seconds": DEFAULT_FRESHNESS_SECONDS,
        "data_mode": "structured_only",
        "timeframes_captured": list(timeframes.keys()),
        "market": {
            "info": info_payload or {},
            "quote": quote_payload or {},
        },
        "timeframes": timeframes,
        "derived_features": derived_features,
        "data_confidence": data_confidence,
        "visual_audit": {
            "enabled": False,
            "required_for_analysis": False,
        },
        "last_error": None,
    }


def build_degraded_payload(symbol: str, previous: dict[str, Any] | None, error: Exception) -> dict[str, Any]:
    payload = dict(previous or {})
    payload["version"] = 2
    payload["owned_by"] = LIVE_STATE_OWNER
    payload["state_version"] = int(payload.get("state_version", 0)) + 1
    payload["updated_at"] = now_iso()
    payload["updated_by"] = LIVE_STATE_READER
    payload["source_runtime"] = OWNER_NAME
    payload["source"] = "TradingView structured live state"
    payload["symbol"] = symbol
    payload["status"] = "degraded"
    payload.setdefault("as_of", now_iso())
    payload.setdefault("fresh_until", payload["as_of"])
    payload["freshness_seconds"] = DEFAULT_FRESHNESS_SECONDS
    payload["data_mode"] = "structured_only"
    payload.setdefault("timeframes_captured", list(payload.get("timeframes", {}).keys()))
    payload.setdefault("market", {"info": {}, "quote": {}})
    payload.setdefault("timeframes", {})
    payload.setdefault("derived_features", build_empty_derived_features())
    payload["data_confidence"] = {
        "status": "DATA_DEGRADED",
        "decision_allowed": False,
        "missing_fields": ["reader.runtime_failure"],
    }
    payload["visual_audit"] = {
        "enabled": False,
        "required_for_analysis": False,
    }
    payload["last_error"] = f"{type(error).__name__}: {error}"
    return payload


def compatibility_replacement(symbol: str) -> str:
    return f"market_runtime/live_state/{symbol_slug(symbol)}.json"


def build_snapshot_mirror_payload(payload: dict[str, Any]) -> dict[str, Any]:
    mirror = json.loads(json.dumps(payload))
    mirror["deprecated"] = True
    mirror["replacement"] = compatibility_replacement(str(payload.get("symbol", "")))
    mirror["data_mode"] = "structured_only"
    return mirror


def write_symbol_payloads(symbol: str, payload: dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        return
    save_json(live_state_path(symbol), payload)
    save_json(snapshot_path(symbol), build_snapshot_mirror_payload(payload))


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    confidence = payload.get("data_confidence", {}) if isinstance(payload, dict) else {}
    return {
        "symbol": payload.get("symbol"),
        "status": payload.get("status"),
        "data_confidence": confidence.get("status"),
        "decision_allowed": confidence.get("decision_allowed"),
        "as_of": payload.get("as_of"),
        "fresh_until": payload.get("fresh_until"),
        "last_error": payload.get("last_error"),
    }


def resolve_next_status(payload: dict[str, Any]) -> str:
    confidence = payload.get("data_confidence", {})
    if confidence.get("status") == "DATA_DEGRADED":
        return "degraded"

    fresh_until_raw = payload.get("fresh_until")
    try:
        fresh_until = datetime.fromisoformat(str(fresh_until_raw))
        return "fresh" if now_local() <= fresh_until else "stale"
    except Exception:
        return "degraded"


def refresh_live_state_statuses() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(LIVE_STATE_DIR.glob("*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue

        symbol = str(payload.get("symbol", path.stem))
        next_status = resolve_next_status(payload)
        if payload.get("status") != next_status:
            payload["status"] = next_status
            payload["updated_at"] = now_iso()
            save_json(path, payload)

        save_json(snapshot_path(symbol), build_snapshot_mirror_payload(payload))
        results.append(summarize_payload(payload))

    return results


def refresh_snapshot_statuses() -> list[dict[str, Any]]:
    return refresh_live_state_statuses()


def capture_symbol(symbol: str, dry_run: bool = False) -> dict[str, Any]:
    primary_path = live_state_path(symbol)
    previous = load_json(primary_path, default=None)
    if not isinstance(previous, dict):
        previous = load_json(snapshot_path(symbol), default={}) or {}

    original_status: dict[str, Any] | None = None
    try:
        with GATEWAY.locked_session(timeout_seconds=240):
            GATEWAY.ensure_connection()
            original_status = GATEWAY.run_tv(["status"], timeout=10)
            info_payload: dict[str, Any] | None = None
            quote_payload: dict[str, Any] | None = None
            timeframes: dict[str, Any] = {}

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

            derived_features, derived_warnings = build_derived_features(symbol, timeframes, quote_payload)
            data_confidence = derive_data_confidence(quote_payload, timeframes, derived_warnings)
            payload = build_live_state_payload(
                symbol=symbol,
                previous=previous,
                info_payload=info_payload,
                quote_payload=quote_payload,
                timeframes=timeframes,
                derived_features=derived_features,
                data_confidence=data_confidence,
            )
    except Exception as exc:
        payload = build_degraded_payload(symbol=symbol, previous=previous, error=exc)
        append_log(f"{symbol} live-state capture failed: {type(exc).__name__}: {exc}")
    finally:
        if original_status:
            original_symbol = original_status.get("chart_symbol")
            original_resolution = original_status.get("chart_resolution")
            if original_symbol and original_resolution:
                try:
                    GATEWAY.ensure_symbol_and_timeframe(str(original_symbol), str(original_resolution))
                except Exception as restore_exc:
                    append_log(
                        f"restore view failed after live-state cycle for {symbol}: "
                        f"{type(restore_exc).__name__}: {restore_exc}"
                    )
        GATEWAY.dismiss_modals()

    write_symbol_payloads(symbol, payload, dry_run=dry_run)
    append_log(f"{symbol} live state captured ({'dry-run' if dry_run else 'live'})")
    return payload


def update_runtime_state(cycle_status: str, symbol_results: list[dict[str, Any]], last_error: str | None = None) -> None:
    payload = {
        "owner": OWNER_NAME,
        "updated_at": now_iso(),
        "status": cycle_status,
        "data_mode": "structured_only",
        "freshness_seconds": DEFAULT_FRESHNESS_SECONDS,
        "symbols": symbol_results,
    }
    if last_error:
        payload["last_error"] = last_error
    save_json(STATE_PATH, payload)


def capture_all(symbol_filter: str | None = None, dry_run: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        if symbol_filter and symbol_filter != symbol and symbol_filter != symbol_slug(symbol):
            continue
        payload = capture_symbol(symbol, dry_run=dry_run)
        results.append(summarize_payload(payload))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture TradingView structured live state for automations.")
    parser.add_argument("--watch", action="store_true", help="Poll continuously instead of running one capture cycle.")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval in seconds.")
    parser.add_argument("--symbol", help="Optional exact symbol filter, e.g. PEPPERSTONE:XAUUSD.")
    parser.add_argument("--dry-run", action="store_true", help="Read live data without writing live-state files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    append_log("structured live-state reader started")

    def run_cycle() -> None:
        refresh_live_state_statuses()
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
                stale_results = refresh_live_state_statuses()
                update_runtime_state(
                    cycle_status="degraded",
                    symbol_results=stale_results,
                    last_error=f"{type(exc).__name__}: {exc}",
                )
                append_log(f"watch cycle failed: {type(exc).__name__}: {exc}")

            time.sleep(max(1, int(args.interval)))
        return 0

    run_cycle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
