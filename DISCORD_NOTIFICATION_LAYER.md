# Discord Notification Layer

## Files

- Config:
  - [`.discord_webhook.env`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/.discord_webhook.env)
- Helper:
  - [`discord_notifier.py`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_notifier.py)
- Watcher bridge launcher:
  - [`start_discord_dispatch_watcher.ps1`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_discord_dispatch_watcher.ps1)
- Long-running watcher:
  - [`discord_dispatch_watcher.py`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_dispatch_watcher.py)
- Enqueue helper:
  - [`discord_enqueue.py`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_enqueue.py)
- Optional manual send bridge:
  - [`send_discord_notification.ps1`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/send_discord_notification.ps1)
- Outbox queue used by all 9 automations:
  - [`discord_payloads/outbox`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_payloads/outbox)
- Sent archive:
  - [`discord_payloads/sent`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_payloads/sent)
- Invalid event quarantine:
  - [`discord_payloads/invalid`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_payloads/invalid)
- Dropped backlog archive:
  - [`discord_payloads/dropped`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_payloads/dropped)
- Legacy mirror only:
  - [`discord_payloads/dispatch.txt`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_payloads/dispatch.txt)
- Runtime log:
  - [`discord_notifier.log`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_notifier.log)
- Watcher runtime log:
  - [`discord_dispatch_watcher.log`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_dispatch_watcher.log)

## Config Priority

The notifier loads the Discord webhook URL in this order:

1. `DISCORD_WEBHOOK_URL` environment variable
2. `.discord_webhook.env`

## Runtime Rule

Notification failures must never break the trading automations.

The helper is intentionally fail-open:

- missing webhook -> log and continue
- empty message -> log and continue
- network / Discord failure -> log and continue

## Verified Fix

The original `403 Forbidden` issue was caused by the webhook helper request shape, not by the workflow logic itself.

The helper now sends Discord requests with:

- `User-Agent`
- `Accept: application/json`
- `?wait=true`

This was verified successfully on `2026-04-20`.

## Current Delivery Flow

The current working architecture is watcher-based with an outbox queue.

All 9 market automations now:

1. build their own trader-facing Discord summary
2. save a human mirror file:
   - `discord_payloads/<automation_id>.txt`
3. enqueue a unique event through:
   - [`discord_enqueue.py`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_enqueue.py)
4. do **not** send network requests directly from inside the automation

The helper writes:

- one per-run event file in `discord_payloads/outbox/*.json`
- one human-readable mirror in `discord_payloads/<automation_id>.txt`
- one legacy `dispatch.txt` mirror for compatibility only

Dry-run tests may set `DISCORD_PAYLOADS_DIR`,
`DISCORD_DISPATCH_STATE_PATH`, and `DISCORD_DISPATCH_LOG_PATH` to point at a
temporary queue. Production automations should leave those variables unset so
the normal `discord_payloads` queue remains the single live transport.

Then the local watcher:

1. stays running outside the automation sandbox
2. polls `discord_payloads/outbox/*.json`
3. sorts events by `created_at`
4. sends each pending event to Discord
5. archives successful events to `discord_payloads/sent/`
6. quarantines corrupt events to `discord_payloads/invalid/`
7. drops stale overflow backlog to `discord_payloads/dropped/`
8. deduplicates by `event_id`, not by message hash

Why this design:

- avoids repeated network permission friction inside the 9 trading automations
- keeps the workflow logic unchanged
- gives one stable Discord send path for every flow
- prevents one automation from overwriting another automation's pending message
- allows recent backlog replay after watcher downtime

## Startup Persistence

The watcher is configured to auto-start with Windows via:

- `C:\Users\sebas\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SMART_MONEY_Discord_Watcher.cmd`

That startup entry launches:

- [`start_discord_dispatch_watcher.ps1`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_discord_dispatch_watcher.ps1)

which then starts:

- [`discord_dispatch_watcher.py`](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_dispatch_watcher.py)

## Discord Message Shape

The stack now uses a communication identity guide at:

- [COMMUNICATION_STYLE_GUIDE.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/COMMUNICATION_STYLE_GUIDE.md)

That guide changes communication only.

- It does **not** change strategy.
- It does **not** change levels, timing states, or risk logic.
- It changes only how the already-decided read is communicated.

The automations no longer use the older ultra-compact templates below as the source of truth.

They now use richer trader-facing summaries per flow, with better visual hierarchy for Discord.

UX/UI principles now applied:

- clear section hierarchy with bold headers
- one main decision block at the end
- statuses and action states in inline code for fast scanning
- fewer dense lines, more grouped information
- levels isolated into their own section
- emojis used as visual anchors, not decoration spam
- each symbol separated like a mini card inside the message
- no long paragraphs inside the notification itself
- short story first, then scan-friendly blocks
- market-first language that feels like a trader live room, not a system monitor
- more energy than reports, without changing the actual thesis or action

Priority rule:

- Discord messages must be trader-facing first and runtime-facing second.
- The first job of every notification is to explain market thesis, setup state,
  levels, and action.
- Runtime or data-quality notes should appear only as a short secondary note
  when they materially limit confidence.
- Do not let notifications turn into system-health alerts when valid market
  data still exists.
- Missing screenshots must never dominate the Discord message because they are
  no longer part of the trading-analysis contract.
- Reserve full `DATA_DEGRADED` notifications for cases where the structured
  live market data itself is stale, missing, or not trustworthy.

Mandatory message shape for Discord:

1. `Historia`
2. `Tesis`
3. `Niveles`
4. `Accion`

Communication rules:

- open with what the market is doing, not with runtime status
- keep the story short and human
- keep the thesis aligned with the engine decision
- mention only the levels that matter to the current read
- close with the exact action now
- use runtime notes only as a short confidence caveat when needed
- if the setup is `TRIGGERED`, the tone should become more direct
- if the setup is `EXPIRED`, say it clearly instead of recycling an old setup as current

## Queue Event Contract

Each outbox event should include:

- `event_id`
- `automation_id`
- `automation_name`
- `created_at`
- `message`
- `message_hash`
- `market_scope`
- `priority`
- `kind`

Rules:

- one automation run should create one event
- each of the 9 market automations must enqueue exactly one event after a run finishes, even when the market decision is `WAIT`, `NO CLEAR EDGE`, or `DATA_DEGRADED`
- deduplication is by `event_id`, not by message hash
- `dispatch.txt` is no longer the authoritative transport
- `dispatch.txt` may remain as a legacy mirror of the most recent enqueued
  message

## Backlog Replay Policy

If the watcher was down, it should replay recent pending events on restart.

Defaults:

- keep only the last `24 hours` of pending events
- send at most `200` pending events per backlog replay window
- if the backlog exceeds those limits:
  - drop older events into `discord_payloads/dropped/`
  - log the drop reason

This prevents:

- losing multiple runs because one shared file was overwritten
- re-sending very old stale messages after a restart
- dropping same-day trading automation runs during normal watcher downtime

Operational sanity check:

- inspect `discord_dispatch_state.json`, `discord_dispatch_watcher.log`,
  `discord_payloads/outbox`, `discord_payloads/sent`,
  `discord_payloads/dropped`, and `discord_payloads/invalid`
- recent same-day market events should move from `outbox` to `sent`
  when the watcher is healthy
- if a run cannot be delivered, `discord_dispatch_state.json` must expose
  `status = DISCORD_DEGRADED`, `dependency_status`, and `last_error`
  instead of silently failing

Runtime wording:

- use `FULL_DATA`, `PARTIAL_DATA`, or `DATA_DEGRADED` for market-data health
- use `CHART_RENDER_DEGRADED` only for chart render verification issues
- use `DISCORD_DEGRADED` only for watcher / delivery failures
- do not mention missing PNGs, screenshot paths, or visual-confidence phrases
  as trading reasons

The live automation prompts in `C:\Users\sebas\.codex\automations\*\automation.toml` are the source of truth.

Typical examples:

### NY Open Levels

```text
[🌅 NY OPEN LEVELS]
📊 **Bias HTF**
🟡 `XAUUSD` → D `<daily bias>` | 4H `<4H bias>` | Align `<alineacion>` | Fuerza `<fuerza>`
🔵 `US30` → D `<daily bias>` | 4H `<4H bias>` | Align `<alineacion>` | Fuerza `<fuerza>`

🧭 **Estructura**
🟡 `XAUUSD` → <estructura actual>
🔵 `US30` → <estructura actual>

🎯 **Niveles**
🟡 `XAUUSD` → <niveles clave dibujados>
🔵 `US30` → <niveles clave dibujados>

✅ **Decision**
Mas limpio: `<simbolo>`
Accion: `<LONGS / SHORTS / WAIT / NO CLEAR EDGE>`
⚠️ Evitar: <lo principal a evitar>
```

### Post Open Validation

```text
[🕘 POST OPEN VALIDATION]
🧪 **Validacion**
🟡 `XAUUSD` → `<valida / rechaza / parcial>`
🔵 `US30` → `<valida / rechaza / parcial>`

📍 **5M / Reaccion**
🟡 `XAUUSD` → <estructura 5m o reaccion clave>
🔵 `US30` → <estructura 5m o reaccion clave>
Nivel clave: <sweep, retest o rechazo mas importante>

✅ **Decision**
Mas limpio: `<simbolo>`
Accion: `<TRADE NOW / WAIT>`
⚠️ Trampa: <trampa principal>
```

### Active Setup Detector

```text
[🎯 ACTIVE SETUP DETECTOR]
🚦 **Estado**
🟡 `XAUUSD` → `<VALID LONG SETUP / VALID SHORT SETUP / WAIT / NO CLEAR EDGE>`
🔵 `US30` → `<VALID LONG SETUP / VALID SHORT SETUP / WAIT / NO CLEAR EDGE>`

⚙️ **Activacion**
🟡 `XAUUSD` → <nivel probado ahora>
🔵 `US30` → <nivel probado ahora>
Trigger: <trigger presente o N/A>
Falta: <confirmacion pendiente o N/A>

✅ **Decision**
Mas limpio: `<simbolo>`
🛑 Evitar: `<simbolo o NINGUNO>`
```

### Bias Integrity Check

```text
[🧱 BIAS INTEGRITY CHECK]
🩺 **Integridad**
🟡 `XAUUSD` → `<BIAS INTACT / BIAS WEAKENED / BIAS INVALIDATED>`
🔵 `US30` → `<BIAS INTACT / BIAS WEAKENED / BIAS INVALIDATED>`

🔑 **Claves**
Sostiene: <nivel o condicion clave>
Fallo: <nivel o condicion clave o NINGUNO>

✅ **Plan**
Mas limpio: `<simbolo>`
Conviccion: `<MANTENER PLAN / REDUCIR CONVICCION>`
```

### Mid-Session Reassessment

```text
[☀️ MID-SESSION REASSESSMENT]
🧭 **Estado Del Dia**
Tesis: `<viva / debilitada / invalidada>`
Oportunidad: `<sigue / ya paso / no hay edge>`

🔍 **Lectura**
🟡 `XAUUSD` → <estado actual>
🔵 `US30` → <estado actual>
Mejor restante: <oportunidad o NINGUNA>

✅ **Decision**
Mas limpio: `<simbolo o NINGUNO>`
Enfoque: `<MOMENTUM / PACIENCIA / NO TRADE>`
⚠️ Trampa: <trampa principal>
```

### End-of-Day Review

```text
[📘 END-OF-DAY REVIEW]
📌 **Resultado**
🟡 `XAUUSD` → <resultado del dia>
🔵 `US30` → <resultado del dia>

📝 **Resumen**
Funciono: <lo que funciono>
Fallo: <lo que fallo>

🌙 **Cierre**
Mas limpio: `<simbolo>`
⚠️ Trampa: <trampa principal>
💡 Leccion: <leccion para manana>
```

### Asia Session Gold

```text
[🌏 ASIA SESSION GOLD]
📊 **Bias HTF**
🟡 `XAUUSD` → D `<daily bias>` | 4H `<4H bias>` | Align `<alineacion>` | Fuerza `<fuerza>`

🧭 **Estructura**
🟡 `XAUUSD` → <estructura actual>

🎯 **Niveles**
🟡 `XAUUSD` → <niveles clave dibujados>

✅ **Decision**
Condicion Asia: `<TRADABLE / MEJOR PACIENCIA>`
Accion: `<LONGS / SHORTS / WAIT / NO CLEAR EDGE>`
⚠️ Evitar: <lo principal a evitar>
```

### Asia Setup Detector

```text
[🌙 ASIA SETUP DETECTOR]
🚦 **Estado**
🟡 `XAUUSD` → `<VALID LONG SETUP / VALID SHORT SETUP / WAIT / NO CLEAR EDGE>`

⚙️ **Activacion**
Nivel clave: <nivel probado ahora>
Trigger: <trigger presente o N/A>
Falta: <confirmacion pendiente o N/A>

✅ **Decision**
Sesgo tactico: `<BREAKOUT / FADE / RANGE>`
Accion: `<EJECUTAR / ESPERAR>`
🛑 Invalida: <nivel o condicion que invalida>
```
