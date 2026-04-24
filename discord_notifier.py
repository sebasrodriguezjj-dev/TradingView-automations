#!/usr/bin/env python3
"""
Fail-open Discord webhook notifier for the TradingView automation engine.

Design goals:
- Keep secrets out of automation prompts.
- Never break the trading workflow if Discord fails.
- Make the config easy to rotate later.
- Keep logs safe by avoiding webhook dumps.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib import parse
from urllib import error, request


WORKSPACE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = WORKSPACE_DIR / ".discord_webhook.env"
DEFAULT_LOG_PATH = WORKSPACE_DIR / "discord_notifier.log"


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_webhook_url(config_path: Path) -> Optional[str]:
    env_value = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if env_value:
        return env_value

    file_values = read_env_file(config_path)
    file_value = file_values.get("DISCORD_WEBHOOK_URL", "").strip()
    if file_value:
        return file_value
    return None


def append_log(log_path: Path, automation: str, message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"{timestamp} | {automation} | {message}\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def build_wait_url(webhook_url: str) -> str:
    parsed = parse.urlsplit(webhook_url)
    query = parse.parse_qsl(parsed.query, keep_blank_values=True)
    keys = {key for key, _ in query}
    if "wait" not in keys:
        query.append(("wait", "true"))
    new_query = parse.urlencode(query)
    return parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))


def send_discord(webhook_url: str, content: str, username: str) -> None:
    payload = json.dumps(
        {
            "content": content,
            "username": username,
        }
    ).encode("utf-8")

    target_url = build_wait_url(webhook_url)
    req = request.Request(
        target_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Codex-Discord-Notifier/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=6) as response:
        status = getattr(response, "status", 200)
        if not 200 <= status < 300:
            raise RuntimeError(f"unexpected Discord status {status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a compact Discord update.")
    parser.add_argument("--automation", required=True, help="Automation name for logs.")
    parser.add_argument("--message", help="Message content to send.")
    parser.add_argument("--message-file", help="UTF-8 text file with the message.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Config file path.")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_PATH), help="Fail-open log path.")
    parser.add_argument(
        "--username",
        default="SMART MONEY - GOOD MONEY",
        help="Discord webhook display name.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    log_path = Path(args.log_file)

    message = (args.message or "").strip()
    if not message and args.message_file:
        message_path = Path(args.message_file)
        if message_path.exists():
            message = message_path.read_text(encoding="utf-8").strip()

    if not message:
        append_log(log_path, args.automation, "skip: empty message")
        return 0

    webhook_url = load_webhook_url(config_path)
    if not webhook_url:
        append_log(log_path, args.automation, "skip: missing webhook configuration")
        return 0

    try:
        send_discord(webhook_url, message, args.username)
        append_log(log_path, args.automation, "sent")
    except Exception as exc:
        # Fail-open by design: trading automations must continue even if Discord is down.
        append_log(log_path, args.automation, f"failed: {type(exc).__name__}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
