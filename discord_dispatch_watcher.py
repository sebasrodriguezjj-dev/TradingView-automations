#!/usr/bin/env python3
"""
Local Discord dispatch watcher for the SMART MONEY - GOOD MONEY engine.

Purpose:
- Watch the shared dispatch file that Codex automations update.
- Send each new dispatch payload to Discord outside the automation sandbox path.
- Avoid duplicate sends by persisting the last delivered content hash.
- Stay fail-open and easy to maintain.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from discord_notifier import send_discord, load_webhook_url


WORKSPACE_DIR = Path(__file__).resolve().parent
DISPATCH_PATH = WORKSPACE_DIR / "discord_payloads" / "dispatch.txt"
CONFIG_PATH = WORKSPACE_DIR / ".discord_webhook.env"
STATE_PATH = WORKSPACE_DIR / "discord_dispatch_state.json"
LOG_PATH = WORKSPACE_DIR / "discord_dispatch_watcher.log"
POLL_SECONDS = 5
USERNAME = "SMART MONEY - GOOD MONEY"
AUTOMATION_NAME = "Discord Dispatch Watcher"


def append_log(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} | {AUTOMATION_NAME} | {message}\n")


def load_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict[str, str]) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_dispatch_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def main() -> int:
    append_log("watcher started")
    state = load_state()
    last_hash = state.get("last_hash", "")

    while True:
        try:
            webhook_url = load_webhook_url(CONFIG_PATH)
            if not webhook_url:
                append_log("skip: missing webhook configuration")
                time.sleep(POLL_SECONDS)
                continue

            dispatch_text = read_dispatch_text(DISPATCH_PATH)
            if not dispatch_text:
                time.sleep(POLL_SECONDS)
                continue

            current_hash = sha256_text(dispatch_text)
            if current_hash == last_hash:
                time.sleep(POLL_SECONDS)
                continue

            send_discord(webhook_url, dispatch_text, USERNAME)
            last_hash = current_hash
            save_state(
                {
                    "last_hash": current_hash,
                    "last_sent_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            append_log("sent")
        except Exception as exc:
            append_log(f"failed: {type(exc).__name__}: {exc}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
