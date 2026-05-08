#!/usr/bin/env python3
"""
Local Discord outbox watcher for the SMART MONEY - GOOD MONEY engine.

Purpose:
- Watch a durable outbox that automations append to.
- Send each queued event to Discord outside the automation sandbox path.
- Avoid duplicate sends per event_id.
- Replay recent backlog after watcher downtime without spamming stale history.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from discord_notifier import send_discord, load_webhook_url


WORKSPACE_DIR = Path(__file__).resolve().parent
PAYLOADS_DIR = Path(os.environ.get("DISCORD_PAYLOADS_DIR", WORKSPACE_DIR / "discord_payloads")).resolve()
OUTBOX_DIR = PAYLOADS_DIR / "outbox"
SENT_DIR = PAYLOADS_DIR / "sent"
INVALID_DIR = PAYLOADS_DIR / "invalid"
DROPPED_DIR = PAYLOADS_DIR / "dropped"
LEGACY_DISPATCH_PATH = PAYLOADS_DIR / "dispatch.txt"
CONFIG_PATH = WORKSPACE_DIR / ".discord_webhook.env"
STATE_PATH = Path(os.environ.get("DISCORD_DISPATCH_STATE_PATH", WORKSPACE_DIR / "discord_dispatch_state.json")).resolve()
LOG_PATH = Path(os.environ.get("DISCORD_DISPATCH_LOG_PATH", WORKSPACE_DIR / "discord_dispatch_watcher.log")).resolve()
POLL_SECONDS = 5
USERNAME = "SMART MONEY - GOOD MONEY"
AUTOMATION_NAME = "Discord Dispatch Watcher"
BACKLOG_MAX_EVENTS = 200
BACKLOG_MAX_AGE_SECONDS = 24 * 60 * 60
DELIVERED_EVENT_MEMORY = 200


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


WATCHER_PID = os.getpid()
WATCHER_STARTED_AT = now_iso()


def classify_dependency_status(error_text: str | None) -> str | None:
    if not error_text:
        return None
    if "WinError 10061" in error_text or "connection refused" in error_text.lower():
        return "discord_connection_refused"
    if "URLError" in error_text:
        return "discord_network_error"
    if "webhook" in error_text.lower():
        return "discord_webhook_configuration"
    return "runtime_error"


def append_log(message: str) -> None:
    timestamp = now_iso()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} | {AUTOMATION_NAME} | {message}\n")


def ensure_dirs() -> None:
    for path in (PAYLOADS_DIR, OUTBOX_DIR, SENT_DIR, INVALID_DIR, DROPPED_DIR):
        path.mkdir(parents=True, exist_ok=True)


def normalize_state(raw_state: dict[str, Any]) -> dict[str, Any]:
    delivered_event_ids = raw_state.get("delivered_event_ids")
    if not isinstance(delivered_event_ids, list):
        delivered_event_ids = []

    return {
        "owner": raw_state.get("owner") or AUTOMATION_NAME,
        "watchdog_pid": raw_state.get("watchdog_pid"),
        "watchdog_started_at": raw_state.get("watchdog_started_at"),
        "heartbeat_at": raw_state.get("heartbeat_at"),
        "status": raw_state.get("status") or ("DISCORD_DEGRADED" if raw_state.get("last_error") else "OK"),
        "delivered_event_ids": delivered_event_ids[-DELIVERED_EVENT_MEMORY:],
        "last_sent_at": raw_state.get("last_sent_at"),
        "last_sent_event_id": raw_state.get("last_sent_event_id"),
        "last_error": raw_state.get("last_error"),
        "dependency_status": raw_state.get("dependency_status"),
        "last_legacy_hash": raw_state.get("last_hash"),
        "backlog_max_events": BACKLOG_MAX_EVENTS,
        "backlog_max_age_seconds": BACKLOG_MAX_AGE_SECONDS,
    }


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return normalize_state({})
    try:
        raw_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return normalize_state({})
    return normalize_state(raw_state)


def save_state(state: dict[str, Any]) -> None:
    state["owner"] = AUTOMATION_NAME
    state["watchdog_pid"] = WATCHER_PID
    state["watchdog_started_at"] = WATCHER_STARTED_AT
    state["heartbeat_at"] = now_iso()
    state["status"] = "DISCORD_DEGRADED" if state.get("last_error") else "OK"
    state["dependency_status"] = classify_dependency_status(state.get("last_error"))
    payload = normalize_state(state)
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def parse_event_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def unique_target_path(target_dir: Path, filename: str) -> Path:
    candidate = target_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = target_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def move_event_file(path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = unique_target_path(target_dir, path.name)
    shutil.move(str(path), str(target_path))
    return target_path


def quarantine_event(path: Path, target_dir: Path, reason: str) -> None:
    moved_path = move_event_file(path, target_dir)
    append_log(f"{reason}: {moved_path.name}")


def read_event_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required_fields = [
        "event_id",
        "automation_id",
        "automation_name",
        "created_at",
        "message",
        "message_hash",
        "market_scope",
        "priority",
        "kind",
    ]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    parse_event_time(payload["created_at"])
    return payload


def delivered_recently(state: dict[str, Any], event_id: str) -> bool:
    return event_id in state.get("delivered_event_ids", [])


def remember_delivery(state: dict[str, Any], event_id: str) -> None:
    delivered = [value for value in state.get("delivered_event_ids", []) if value != event_id]
    delivered.append(event_id)
    state["delivered_event_ids"] = delivered[-DELIVERED_EVENT_MEMORY:]


def load_pending_events(state: dict[str, Any]) -> list[tuple[Path, dict[str, Any], datetime]]:
    now = datetime.now().astimezone()
    pending: list[tuple[Path, dict[str, Any], datetime]] = []

    for path in sorted(OUTBOX_DIR.glob("*.json")):
        try:
            payload = read_event_payload(path)
            created_at = parse_event_time(payload["created_at"])
        except Exception as exc:
            quarantine_event(path, INVALID_DIR, f"invalid event ({type(exc).__name__}: {exc})")
            continue

        event_id = str(payload["event_id"])
        if delivered_recently(state, event_id):
            quarantine_event(path, SENT_DIR, f"duplicate event_id skipped ({event_id})")
            continue

        pending.append((path, payload, created_at))

    pending.sort(key=lambda item: (item[2], item[0].name))

    recent_cutoff = now - timedelta(seconds=BACKLOG_MAX_AGE_SECONDS)
    recent_events: list[tuple[Path, dict[str, Any], datetime]] = []

    for path, payload, created_at in pending:
        if created_at < recent_cutoff:
            quarantine_event(path, DROPPED_DIR, "dropped backlog event by age")
            continue
        recent_events.append((path, payload, created_at))

    if len(recent_events) > BACKLOG_MAX_EVENTS:
        overflow = len(recent_events) - BACKLOG_MAX_EVENTS
        for path, _, _ in recent_events[:overflow]:
            quarantine_event(path, DROPPED_DIR, "dropped backlog event by count limit")
        recent_events = recent_events[overflow:]

    return recent_events


def dispatch_event(webhook_url: str, payload: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        append_log(f"dry-run: would send {payload['event_id']} from {payload['automation_id']}")
        return
    send_discord(webhook_url, str(payload["message"]), USERNAME)


def process_once(dry_run: bool = False) -> int:
    ensure_dirs()
    state = load_state()
    webhook_url = load_webhook_url(CONFIG_PATH)
    if not webhook_url and not dry_run:
        state["last_error"] = "missing webhook configuration"
        save_state(state)
        append_log("skip: missing webhook configuration")
        return 0

    pending_events = load_pending_events(state)
    if not pending_events:
        save_state(state)
        return 0

    for path, payload, _ in pending_events:
        try:
            dispatch_event(webhook_url or "", payload, dry_run=dry_run)
        except Exception as exc:
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            save_state(state)
            append_log(f"failed {payload['event_id']} from {payload['automation_id']}: {type(exc).__name__}: {exc}")
            return 0

        if not dry_run:
            remember_delivery(state, str(payload["event_id"]))
            state["last_sent_at"] = now_iso()
            state["last_sent_event_id"] = payload["event_id"]
            state["last_error"] = None
            save_state(state)
            move_event_file(path, SENT_DIR)
            append_log(f"sent {payload['event_id']} from {payload['automation_id']}")
        else:
            append_log(f"dry-run validated {payload['event_id']} from {payload['automation_id']}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch the Discord outbox and send pending events.")
    parser.add_argument("--once", action="store_true", help="Process the queue once and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Do not send or archive; only validate pending events.")
    args = parser.parse_args()

    ensure_dirs()
    append_log("watcher started")

    if args.once:
        return process_once(dry_run=args.dry_run)

    while True:
        try:
            process_once(dry_run=args.dry_run)
        except Exception as exc:
            state = load_state()
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            save_state(state)
            append_log(f"failed: {type(exc).__name__}: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
