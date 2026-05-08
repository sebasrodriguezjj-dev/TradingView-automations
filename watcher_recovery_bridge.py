#!/usr/bin/env python3
"""
Blind full-recovery bridge for the SMART MONEY - GOOD MONEY watcher stack.

Purpose:
- Launch the official recovery reassessment through `codex exec`.
- Verify that desired_state was refreshed after a runtime stall.
- Verify that the chart runtime re-synced to the refreshed desired state.
- Optionally enqueue a compact post-recovery Discord notification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import market_snapshotter


WORKSPACE_DIR = Path(__file__).resolve().parent
MARKET_RUNTIME_DIR = WORKSPACE_DIR / "market_runtime"
CHART_RUNTIME_DIR = WORKSPACE_DIR / "chart_runtime"
DESIRED_STATES_DIR = CHART_RUNTIME_DIR / "desired_states"
APPLIED_STATES_DIR = CHART_RUNTIME_DIR / "applied_states"
CHART_HEALTH_PATH = CHART_RUNTIME_DIR / "chart_runtime_state.json"
LOCK_PATH = MARKET_RUNTIME_DIR / "recovery.lock.json"
RESULT_PATH = MARKET_RUNTIME_DIR / "recovery_bridge_result.json"
MESSAGE_PATH = MARKET_RUNTIME_DIR / "recovery_bridge_last_message.txt"
SPEC_PATH = WORKSPACE_DIR / "WATCHER_RECOVERY_REASSESSMENT.md"
LOG_PATH = MARKET_RUNTIME_DIR / "watcher_recovery_bridge.log"
DISCORD_ENQUEUE_PATH = WORKSPACE_DIR / "discord_enqueue.py"
SYMBOLS = [
    "PEPPERSTONE:XAUUSD",
    "FOREXCOM:US30",
]
ACTIVE_RECOVERY_PHASES = {
    "bootstrap_preflight",
    "infra_recovering",
    "data_recovering",
    "reassess_pending",
    "reassess_running",
    "chart_sync_pending",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


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


def append_log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{now_iso()} | SMART MONEY - GOOD MONEY Recovery Bridge | {message}\n")


def symbol_slug(symbol: str) -> str:
    return symbol.replace(":", "_").replace("/", "_").replace(" ", "_")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def json_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def desired_state_path(symbol: str) -> Path:
    return DESIRED_STATES_DIR / f"{symbol_slug(symbol)}.json"


def applied_state_path(symbol: str) -> Path:
    return APPLIED_STATES_DIR / f"{symbol_slug(symbol)}.json"


def pid_is_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        if os.name == "nt":
            return subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            ).stdout.strip() == str(int(pid))
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def acquire_lock(attempt_id: str) -> dict[str, Any]:
    existing = load_json(LOCK_PATH, default={}) or {}
    existing_phase = str(existing.get("recovery_phase") or "")
    existing_updated_at = parse_iso_datetime(existing.get("updated_at"))
    existing_pid = existing.get("pid")
    is_stale = False
    if existing_updated_at is not None:
        is_stale = datetime.now().astimezone() - existing_updated_at > timedelta(minutes=15)

    if existing and existing_phase in ACTIVE_RECOVERY_PHASES and pid_is_running(existing_pid) and not is_stale:
        raise RuntimeError(
            f"Recovery lock already active for attempt {existing.get('attempt_id')} "
            f"(phase={existing_phase}, pid={existing_pid})."
        )

    payload = {
        "owner": "SMART MONEY - GOOD MONEY Recovery Bridge",
        "pid": os.getpid(),
        "attempt_id": attempt_id,
        "updated_at": now_iso(),
        "recovery_phase": "reassess_running",
        "spec_path": str(SPEC_PATH),
    }
    save_json(LOCK_PATH, payload)
    return payload


def release_lock(attempt_id: str) -> None:
    existing = load_json(LOCK_PATH, default={}) or {}
    if not existing:
        return
    if str(existing.get("attempt_id")) != attempt_id:
        return
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass


def build_prompt(spec_text: str, attempt_id: str, requested_at: str, recovery_reason: str) -> str:
    return (
        "Execute the blind watcher recovery reassessment now.\n\n"
        f"Recovery attempt id: {attempt_id}\n"
        f"Recovery requested at: {requested_at}\n"
        f"Recovery reason: {recovery_reason}\n\n"
        "Use the following spec exactly. This is a recovery continuation only.\n"
        "Do not change the strategy, risk, timing states, chart ownership, or drawing vocabulary.\n"
        "Do not enqueue Discord yourself; the watcher recovery bridge owns post-recovery notification.\n"
        "If the recovery conclusion is that the current desired levels remain valid, still rewrite both desired_state JSON files "
        "for XAUUSD and US30 with refresh_reason = stall_recovery, a fresh updated_at, and a bumped state_version so the runtime can "
        "acknowledge the recovery and force a clean redraw.\n"
        "Finish with a concise trader-facing message using: Historia, Tesis, Niveles, Accion.\n\n"
        f"{spec_text}\n"
    )


def run_codex_reassessment(prompt_text: str, timeout_seconds: int) -> tuple[int, str]:
    MESSAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MESSAGE_PATH.exists():
        MESSAGE_PATH.unlink(missing_ok=True)

    command = [
        "codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "-C",
        str(WORKSPACE_DIR),
        "--output-last-message",
        str(MESSAGE_PATH),
        prompt_text,
    ]

    append_log("launching codex recovery reassessment")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    append_log(f"codex recovery reassessment finished with exit code {result.returncode}")
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    return result.returncode, stderr or stdout


def desired_states_refreshed_since(requested_at: str) -> bool:
    return market_snapshotter.desired_states_refreshed_since(requested_at, symbols=SYMBOLS)


def chart_symbol_in_sync(symbol: str, requested_at: str) -> tuple[bool, str]:
    desired_state = load_json(desired_state_path(symbol), default={}) or {}
    applied_state = load_json(applied_state_path(symbol), default={}) or {}
    chart_health = load_json(CHART_HEALTH_PATH, default={}) or {}

    if not desired_state:
        return False, f"{symbol} desired_state missing"
    if not applied_state:
        return False, f"{symbol} applied_state missing"

    desired_hash = json_sha256(desired_state)
    if applied_state.get("desired_hash") != desired_hash:
        return False, f"{symbol} applied desired_hash mismatch"

    desired_updated_at = parse_iso_datetime(desired_state.get("updated_at"))
    requested_at_dt = parse_iso_datetime(requested_at)
    if desired_updated_at is None or requested_at_dt is None or desired_updated_at < requested_at_dt:
        return False, f"{symbol} desired_state not refreshed after recovery request"

    symbol_health = ((chart_health.get("symbols") or {}).get(symbol)) or {}
    status = str(symbol_health.get("status") or "")
    if status not in {"verified", "noop", "dry-run"}:
        return False, f"{symbol} chart status not synced ({status or 'missing'})"

    chart_event_time = parse_iso_datetime(
        symbol_health.get("last_noop_at")
        or symbol_health.get("last_success_at")
        or symbol_health.get("last_apply_started_at")
    )
    if chart_event_time is None or chart_event_time < desired_updated_at:
        return False, f"{symbol} chart sync timestamp is older than desired_state"

    return True, "ok"


def wait_for_chart_sync(requested_at: str, timeout_seconds: int) -> tuple[bool, list[str]]:
    deadline = time.time() + timeout_seconds
    last_reasons: list[str] = []

    while time.time() < deadline:
        reasons: list[str] = []
        all_synced = True
        for symbol in SYMBOLS:
            synced, reason = chart_symbol_in_sync(symbol, requested_at)
            if not synced:
                all_synced = False
                reasons.append(reason)
        if all_synced:
            return True, []
        last_reasons = reasons
        time.sleep(5)

    return False, last_reasons


def fallback_message(success: bool, failure_reason: str | None = None) -> str:
    if success:
        return (
            "Historia:\n"
            "La infraestructura volvió y el reassessment de recuperación cerró el ciclo completo.\n\n"
            "Tesis:\n"
            "La estrategia no cambió; el stack volvió a quedar operativo con un mapa live actualizado o revalidado.\n\n"
            "Niveles:\n"
            "Se preservan o refrescan solo los niveles que el reassessment oficial dejó vivos en desired_state.\n\n"
            "Accion:\n"
            "Volver a seguir el mapa activo. Si el setup ya corrió, no chase; esperar el retest que el reassessment dejó vigente."
        )

    reason = failure_reason or "el recovery no pudo cerrar desired_state + chart sync"
    return (
        "Historia:\n"
        "La recuperación automática levantó parte de la infraestructura, pero no cerró el ciclo completo.\n\n"
        "Tesis:\n"
        f"La estrategia no cambió, pero el dato live no quedó trader-usable todavía porque {reason}.\n\n"
        "Niveles:\n"
        "Se preserva el último mapa deseado válido; no se promociona una entrada nueva desde un recovery incompleto.\n\n"
        "Accion:\n"
        "WAIT. No operar este runtime hasta que vuelva una recuperación completa y el redraw quede verificado."
    )


def maybe_enqueue_notification(message_path: Path, success: bool) -> tuple[bool, str | None]:
    if not message_path.exists() or not message_path.read_text(encoding="utf-8").strip():
        return False, "message missing"

    command = [
        sys.executable,
        str(DISCORD_ENQUEUE_PATH),
        "--automation-id",
        "watcher-recovery-bridge",
        "--automation-name",
        "Watcher Recovery Bridge",
        "--message-file",
        str(message_path),
        "--market-scope",
        "both",
        "--priority",
        "high" if success else "ops",
        "--kind",
        "market_notification" if success else "ops_notification",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "").strip() or "discord enqueue failed"
    return True, None


def write_result(payload: dict[str, Any]) -> None:
    save_json(RESULT_PATH, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the blind watcher recovery reassessment bridge.")
    parser.add_argument("--attempt-id", default=uuid.uuid4().hex[:12])
    parser.add_argument("--requested-at", required=True)
    parser.add_argument("--recovery-reason", default="stall_recovery")
    parser.add_argument("--codex-timeout-seconds", type=int, default=420)
    parser.add_argument("--chart-sync-timeout-seconds", type=int, default=90)
    parser.add_argument("--notify", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = now_iso()
    attempt_id = str(args.attempt_id)
    result_payload: dict[str, Any] = {
        "owner": "SMART MONEY - GOOD MONEY Recovery Bridge",
        "attempt_id": attempt_id,
        "requested_at": args.requested_at,
        "started_at": started_at,
        "spec_path": str(SPEC_PATH),
        "message_path": str(MESSAGE_PATH),
        "result_path": str(RESULT_PATH),
        "status": "running",
    }
    write_result(result_payload)

    try:
        acquire_lock(attempt_id)
        if not SPEC_PATH.exists():
            raise RuntimeError(f"Recovery spec missing: {SPEC_PATH}")

        prompt_text = build_prompt(
            spec_text=SPEC_PATH.read_text(encoding="utf-8"),
            attempt_id=attempt_id,
            requested_at=args.requested_at,
            recovery_reason=args.recovery_reason,
        )
        exit_code, codex_error = run_codex_reassessment(prompt_text, timeout_seconds=args.codex_timeout_seconds)
        result_payload["codex_exit_code"] = exit_code
        result_payload["codex_error"] = codex_error or None

        if exit_code != 0:
            raise RuntimeError(codex_error or f"codex exec failed with exit code {exit_code}")

        if not desired_states_refreshed_since(args.requested_at):
            raise RuntimeError("desired_state files were not refreshed after recovery request")

        synced, sync_reasons = wait_for_chart_sync(
            requested_at=args.requested_at,
            timeout_seconds=args.chart_sync_timeout_seconds,
        )
        result_payload["chart_sync_verified"] = synced
        result_payload["chart_sync_reasons"] = sync_reasons
        if not synced:
            raise RuntimeError("; ".join(sync_reasons) or "chart sync did not verify in time")

        if not MESSAGE_PATH.exists() or not MESSAGE_PATH.read_text(encoding="utf-8").strip():
            MESSAGE_PATH.write_text(fallback_message(success=True), encoding="utf-8")

        notification_sent = False
        notification_error = None
        if args.notify:
            notification_sent, notification_error = maybe_enqueue_notification(MESSAGE_PATH, success=True)

        result_payload.update(
            {
                "status": "success",
                "finished_at": now_iso(),
                "desired_state_refreshed": True,
                "chart_sync_verified": True,
                "chart_sync_verified_at": now_iso(),
                "notification_sent": notification_sent,
                "notification_error": notification_error,
                "last_message_path": str(MESSAGE_PATH),
            }
        )
        write_result(result_payload)
        append_log(f"recovery bridge succeeded for attempt {attempt_id}")
        return 0
    except Exception as exc:
        failure_reason = f"{type(exc).__name__}: {exc}"
        append_log(f"recovery bridge failed for attempt {attempt_id}: {failure_reason}")
        if not MESSAGE_PATH.exists() or not MESSAGE_PATH.read_text(encoding="utf-8").strip():
            MESSAGE_PATH.write_text(fallback_message(success=False, failure_reason=str(exc)), encoding="utf-8")

        notification_sent = False
        notification_error = None
        if args.notify:
            notification_sent, notification_error = maybe_enqueue_notification(MESSAGE_PATH, success=False)

        result_payload.update(
            {
                "status": "failed",
                "finished_at": now_iso(),
                "desired_state_refreshed": desired_states_refreshed_since(args.requested_at),
                "last_error": failure_reason,
                "notification_sent": notification_sent,
                "notification_error": notification_error,
                "last_message_path": str(MESSAGE_PATH),
            }
        )
        write_result(result_payload)
        return 1
    finally:
        release_lock(attempt_id)


if __name__ == "__main__":
    raise SystemExit(main())
