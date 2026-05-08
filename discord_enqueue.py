#!/usr/bin/env python3
"""
Deterministic Discord outbox writer for SMART MONEY - GOOD MONEY automations.

Purpose:
- Give every automation run its own Discord event.
- Keep a human-readable per-automation mirror file.
- Decouple message production from the watcher send loop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


WORKSPACE_DIR = Path(__file__).resolve().parent
PAYLOADS_DIR = Path(os.environ.get("DISCORD_PAYLOADS_DIR", WORKSPACE_DIR / "discord_payloads")).resolve()
OUTBOX_DIR = PAYLOADS_DIR / "outbox"
LEGACY_DISPATCH_PATH = PAYLOADS_DIR / "dispatch.txt"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_token(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    cleaned = cleaned.strip("-")
    return cleaned or "automation"


def event_timestamp_token(created_at: str) -> str:
    return (
        created_at.replace("-", "")
        .replace(":", "")
        .replace("+", "Z")
        .replace(".", "")
    )


def read_message(inline_message: str, message_file: Optional[str]) -> str:
    message = inline_message.strip()
    if message:
        return message

    if message_file:
        path = Path(message_file)
        if path.exists():
            return path.read_text(encoding="utf-8").strip()

    return ""


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def build_event_payload(
    automation_id: str,
    automation_name: str,
    message: str,
    market_scope: str,
    priority: str,
    kind: str,
) -> dict:
    created_at = now_iso()
    event_id = uuid.uuid4().hex
    return {
        "event_id": event_id,
        "automation_id": automation_id,
        "automation_name": automation_name,
        "created_at": created_at,
        "message": message,
        "message_hash": sha256_text(message),
        "market_scope": market_scope,
        "priority": priority,
        "kind": kind,
    }


def build_event_path(payload: dict) -> Path:
    timestamp = event_timestamp_token(payload["created_at"])
    automation_id = sanitize_token(payload["automation_id"])
    event_id = sanitize_token(payload["event_id"])
    return OUTBOX_DIR / f"{timestamp}_{automation_id}_{event_id}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Enqueue a Discord event for the local watcher.")
    parser.add_argument("--automation-id", required=True)
    parser.add_argument("--automation-name", required=True)
    parser.add_argument("--message", default="")
    parser.add_argument("--message-file")
    parser.add_argument(
        "--market-scope",
        choices=["xauusd", "us30", "both", "ops"],
        default="both",
    )
    parser.add_argument(
        "--priority",
        choices=["normal", "high", "ops"],
        default="normal",
    )
    parser.add_argument(
        "--kind",
        choices=["market_notification", "ops_notification"],
        default="market_notification",
    )
    args = parser.parse_args()

    message = read_message(args.message, args.message_file)
    if not message:
        raise SystemExit("Message is empty. Provide --message or --message-file.")

    PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    payload = build_event_payload(
        automation_id=args.automation_id,
        automation_name=args.automation_name,
        message=message,
        market_scope=args.market_scope,
        priority=args.priority,
        kind=args.kind,
    )

    mirror_path = PAYLOADS_DIR / f"{sanitize_token(args.automation_id)}.txt"
    event_path = build_event_path(payload)

    atomic_write_text(mirror_path, message)
    atomic_write_text(LEGACY_DISPATCH_PATH, message)
    atomic_write_json(event_path, payload)

    print(
        json.dumps(
            {
                "owner": "SMART MONEY - GOOD MONEY Discord Enqueue",
                "automation_id": args.automation_id,
                "automation_name": args.automation_name,
                "event_id": payload["event_id"],
                "event_path": str(event_path),
                "mirror_path": str(mirror_path),
                "created_at": payload["created_at"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
