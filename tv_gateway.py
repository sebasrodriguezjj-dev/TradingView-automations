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
import socket
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


WORKSPACE_DIR = Path(__file__).resolve().parent
TV_ENTRY = Path(r"C:\Users\sebas\tradingview-mcp\src\cli\index.js")
LOCK_PATH = WORKSPACE_DIR / "tv_gateway.lock"
STATE_PATH = WORKSPACE_DIR / "tv_gateway_state.json"
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
        self.state_path = STATE_PATH
        self._owns_lock = False

    def append_log(self, message: str) -> None:
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{now_iso()} | {self.owner_name} | {message}\n")

    def _read_lock_payload(self) -> dict[str, Any] | None:
        if not self.lock_path.exists():
            return None
        try:
            return json.loads(self.lock_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_gateway_state(
        self,
        status: str,
        operation: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        lock_payload = self._read_lock_payload()
        payload = {
            "owner": "SMART MONEY - GOOD MONEY TradingView Gateway",
            "updated_at": now_iso(),
            "status": status,
            "client_owner": self.owner_name,
            "client_pid": os.getpid(),
            "operation": operation,
            "last_error": error,
            "lock": lock_payload,
        }
        try:
            self.state_path.write_text(
                json.dumps(payload, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def run_tv(
        self,
        args: list[str],
        timeout: int = 30,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        if not self._owns_lock:
            lock_timeout = max(timeout + 30, 60)
            with self.locked_session(timeout_seconds=lock_timeout):
                return self.run_tv(args, timeout=timeout, cwd=cwd)

        command = ["node", str(self.tv_entry), *args]
        self._touch_lock(operation=args)
        self._write_gateway_state("running", operation=args)

        try:
            result = subprocess.run(
                command,
                cwd=str(cwd or self.workspace_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            error_text = f"TimeoutExpired: {exc}"
            self._write_gateway_state("degraded", operation=args, error=error_text)
            raise

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
            self._write_gateway_state("degraded", operation=args, error=error_text)
            raise TvCliError(f"tv {' '.join(args)} failed ({result.returncode}): {error_text}")

        self._write_gateway_state("healthy", operation=args)
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

    def _cdp_port_responding(
        self,
        host: str = "127.0.0.1",
        port: int = 9222,
        timeout_seconds: float = 1.0,
    ) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout_seconds):
                return True
        except OSError:
            return False

    def _kill_tradingview_processes(self) -> None:
        if os.name != "nt":
            try:
                subprocess.run(
                    ["pkill", "-f", "TradingView"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except Exception as exc:
                self.append_log(f"pkill TradingView failed: {exc}")
            return

        kill_commands = [
            ["taskkill", "/F", "/T", "/IM", "TradingView.exe"],
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process TradingView -ErrorAction SilentlyContinue | Stop-Process -Force",
            ],
        ]

        for command in kill_commands:
            try:
                subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except Exception as exc:
                self.append_log(f"TradingView kill command failed ({command[0]}): {exc}")

    def _hard_relaunch(self) -> None:
        self.append_log("starting hard TradingView relaunch")
        self._kill_tradingview_processes()
        time.sleep(3)
        self.try_tv(["launch"], timeout=30)
        time.sleep(6)
        self.dismiss_modals()

    def ensure_connection(self) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return self.run_tv(["status"], timeout=10)
            except Exception as exc:
                last_error = exc
                self.append_log(f"status check attempt {attempt + 1} failed: {exc}")
                time.sleep(1)

        self.append_log(f"status check failed, attempting launch: {last_error}")
        self.try_tv(["launch"], timeout=20)
        time.sleep(4)
        self.dismiss_modals()

        for attempt in range(2):
            try:
                return self.run_tv(["status"], timeout=10)
            except Exception as exc:
                last_error = exc
                self.append_log(f"post-launch status attempt {attempt + 1} failed: {exc}")
                time.sleep(1)

        self.append_log(
            "soft TradingView recovery failed; attempting hard relaunch "
            f"(cdp_port_responding={self._cdp_port_responding()})"
        )
        self._hard_relaunch()

        for attempt in range(3):
            try:
                return self.run_tv(["status"], timeout=12)
            except Exception as exc:
                last_error = exc
                self.append_log(f"post-hard-relaunch status attempt {attempt + 1} failed: {exc}")
                time.sleep(2)

        assert last_error is not None
        raise last_error

    def _pid_is_running(self, pid: int | None) -> bool:
        if not pid or pid <= 0:
            return False
        if os.name == "nt":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32
                process_query_limited_information = 0x1000
                handle = kernel32.OpenProcess(
                    process_query_limited_information,
                    False,
                    int(pid),
                )
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            except Exception:
                return False
        try:
            os.kill(pid, 0)
        except PermissionError:
            return True
        except OSError:
            return False
        return True

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

    def _lock_payload(self, operation: list[str] | None = None) -> dict[str, Any]:
        return {
            "owner": self.owner_name,
            "pid": os.getpid(),
            "acquired_at": now_iso(),
            "heartbeat_at": now_iso(),
            "operation": operation,
        }

    def _write_lock_payload(self, payload: dict[str, Any]) -> None:
        self.lock_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _touch_lock(self, operation: list[str] | None = None) -> None:
        if not self._owns_lock or not self.lock_path.exists():
            return
        payload = self._read_lock_payload() or {}
        if payload.get("pid") != os.getpid():
            return
        payload.update(
            {
                "owner": self.owner_name,
                "pid": os.getpid(),
                "heartbeat_at": now_iso(),
                "operation": operation,
            }
        )
        if not payload.get("acquired_at"):
            payload["acquired_at"] = now_iso()
        try:
            self._write_lock_payload(payload)
        except OSError:
            pass

    def _remove_stale_lock_if_needed(self) -> None:
        if not self.lock_path.exists():
            return
        payload = self._read_lock_payload() or {}
        owner_pid = payload.get("pid")
        try:
            owner_pid = int(owner_pid) if owner_pid is not None else None
        except (TypeError, ValueError):
            owner_pid = None

        try:
            last_heartbeat_raw = payload.get("heartbeat_at") or payload.get("acquired_at")
            if last_heartbeat_raw:
                last_heartbeat = datetime.fromisoformat(str(last_heartbeat_raw))
                age_seconds = time.time() - last_heartbeat.timestamp()
            else:
                age_seconds = time.time() - self.lock_path.stat().st_mtime
        except OSError:
            return
        except Exception:
            age_seconds = time.time() - self.lock_path.stat().st_mtime

        owner_running = self._pid_is_running(owner_pid)
        if owner_running and age_seconds < STALE_LOCK_SECONDS:
            return

        if owner_running and age_seconds >= STALE_LOCK_SECONDS:
            reason = f"stale live owner pid {owner_pid}; last heartbeat {int(age_seconds)}s ago"
        elif owner_pid:
            reason = f"dead owner pid {owner_pid}"
        else:
            reason = "missing owner pid"

        try:
            self.lock_path.unlink()
            self.append_log(f"removed TradingView lock ({reason})")
            self._write_gateway_state("recovered", error=f"removed lock: {reason}")
        except OSError:
            pass

    def _try_acquire_lock(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(self._lock_payload(), ensure_ascii=True, indent=2))
        self._owns_lock = True
        self._write_gateway_state("lock_acquired")
        return True

    def _release_lock(self) -> None:
        try:
            if self.lock_path.exists():
                payload = self._read_lock_payload() or {}
                if payload.get("pid") == os.getpid():
                    self.lock_path.unlink()
        except OSError:
            pass
        finally:
            self._owns_lock = False

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
