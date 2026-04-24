#!/usr/bin/env python3
"""
Shared TradingView CLI access layer for local runtimes.

This module centralizes:
- direct `tv` CLI invocation
- modal dismissal
- connection recovery
- symbol/timeframe readiness checks
- a cross-process lock so the chart executor and market snapshotter do not
  interleave TradingView commands
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


WORKSPACE_DIR = Path(__file__).resolve().parent
TV_ENTRY = Path(r"C:\Users\sebas\tradingview-mcp\src\cli\index.js")
LOCK_PATH = WORKSPACE_DIR / "tv_gateway.lock"
STALE_LOCK_SECONDS = 300
KNOWN_MODAL_ESCAPES = [
    ["ui", "keyboard", "Escape"],
]


class TvCliError(RuntimeError):
    """Raised when the TradingView CLI returns a non-zero exit code."""


class TvLockTimeout(RuntimeError):
    """Raised when the shared TradingView lock cannot be acquired in time."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def symbol_slug(symbol: str) -> str:
    return symbol.replace(":", "_").replace("/", "_").replace(" ", "_")


def timeframe_to_seconds(timeframe: str) -> int:
    normalized = (timeframe or "5").strip().upper()
    if normalized.isdigit():
        return int(normalized) * 60
    if normalized.endswith("H") and normalized[:-1].isdigit():
        return int(normalized[:-1]) * 3600
    if normalized == "D":
        return 86400
    if normalized == "W":
        return 604800
    if normalized == "M":
        return 2592000
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def timeframe_aliases(timeframe: str) -> set[str]:
    normalized = (timeframe or "5").strip().upper()
    aliases = {normalized}

    if normalized in {"D", "1D"}:
        aliases.update({"D", "1D"})
    elif normalized in {"W", "1W"}:
        aliases.update({"W", "1W"})
    elif normalized in {"M", "1M"}:
        aliases.update({"M", "1M"})
    elif normalized.endswith("H") and normalized[:-1].isdigit():
        aliases.add(str(int(normalized[:-1]) * 60))
    elif normalized.isdigit():
        minutes = int(normalized)
        if minutes >= 60 and minutes % 60 == 0:
            aliases.add(f"{minutes // 60}H")

    return aliases


def timeframes_match(requested: str, actual: str) -> bool:
    return not timeframe_aliases(requested).isdisjoint(timeframe_aliases(actual))


class TvGateway:
    def __init__(
        self,
        owner_name: str,
        log_path: Path | None,
        workspace_dir: Path | None = None,
        lock_path: Path | None = None,
    ) -> None:
        self.owner_name = owner_name
        self.log_path = log_path
        self.workspace_dir = workspace_dir or WORKSPACE_DIR
        self.lock_path = lock_path or LOCK_PATH
        self.tv_entry = TV_ENTRY

    def append_log(self, message: str) -> None:
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{now_iso()} | {self.owner_name} | {message}\n")

    def run_tv(
        self,
        args: list[str],
        timeout: int = 30,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        command = ["node", str(self.tv_entry), *args]
        result = subprocess.run(
            command,
            cwd=str(cwd or self.workspace_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        payload: dict[str, Any] = {}
        if stdout:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = {"success": result.returncode == 0, "raw_stdout": stdout}

        if result.returncode != 0:
            error_text = stderr or stdout or "Unknown TradingView CLI error"
            raise TvCliError(f"tv {' '.join(args)} failed ({result.returncode}): {error_text}")

        return payload

    def try_tv(
        self,
        args: list[str],
        timeout: int = 15,
        cwd: Path | None = None,
    ) -> dict[str, Any] | None:
        try:
            return self.run_tv(args, timeout=timeout, cwd=cwd)
        except Exception:
            return None

    def dismiss_modals(self) -> None:
        for args in KNOWN_MODAL_ESCAPES:
            self.try_tv(args, timeout=5)

    def ensure_connection(self) -> dict[str, Any]:
        try:
            return self.run_tv(["status"], timeout=10)
        except Exception as exc:
            self.append_log(f"status check failed, attempting launch: {exc}")
            self.try_tv(["launch"], timeout=20)
            time.sleep(4)
            self.dismiss_modals()
            return self.run_tv(["status"], timeout=10)

    def wait_for_chart_ready(
        self,
        symbol: str,
        timeframe: str,
        attempts: int = 12,
        sleep_seconds: float = 1.0,
    ) -> dict[str, Any]:
        last_status: dict[str, Any] | None = None
        for _ in range(attempts):
            try:
                last_status = self.run_tv(["status"], timeout=10)
            except Exception:
                last_status = None

            if (
                last_status
                and last_status.get("chart_symbol") == symbol
                and timeframes_match(str(timeframe), str(last_status.get("chart_resolution")))
                and bool(last_status.get("api_available"))
            ):
                return last_status

            time.sleep(sleep_seconds)

        raise RuntimeError(
            f"Chart did not become ready for {symbol} {timeframe}. Last status: {last_status}"
        )

    def ensure_symbol_and_timeframe(self, symbol: str, timeframe: str) -> None:
        current = self.run_tv(["status"], timeout=10)
        if current.get("chart_symbol") != symbol:
            self.run_tv(["symbol", symbol], timeout=15)
        if not timeframes_match(str(timeframe), str(current.get("chart_resolution"))):
            self.run_tv(["timeframe", str(timeframe)], timeout=15)
        self.wait_for_chart_ready(symbol, timeframe)

    def _lock_payload(self) -> str:
        return json.dumps(
            {
                "owner": self.owner_name,
                "pid": os.getpid(),
                "acquired_at": now_iso(),
            },
            ensure_ascii=True,
            indent=2,
        )

    def _remove_stale_lock_if_needed(self) -> None:
        if not self.lock_path.exists():
            return
        try:
            age_seconds = time.time() - self.lock_path.stat().st_mtime
        except OSError:
            return
        if age_seconds >= STALE_LOCK_SECONDS:
            try:
                self.lock_path.unlink()
                self.append_log("removed stale TradingView lock")
            except OSError:
                pass

    def _try_acquire_lock(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(self._lock_payload())
        return True

    def _release_lock(self) -> None:
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except OSError:
            pass

    @contextmanager
    def locked_session(
        self,
        timeout_seconds: int = 120,
        poll_seconds: float = 0.25,
    ) -> Iterator[None]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            self._remove_stale_lock_if_needed()
            if self._try_acquire_lock():
                try:
                    yield
                finally:
                    self._release_lock()
                return
            time.sleep(poll_seconds)

        raise TvLockTimeout(
            f"Timed out acquiring TradingView gateway lock for {self.owner_name}"
        )
