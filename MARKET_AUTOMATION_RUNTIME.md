# Market Automation Runtime

## Goal

Keep the existing SMART MONEY - GOOD MONEY strategy intact while moving live
TradingView reads out of the Codex automation path.

The analytical workflows keep doing the same job:

- read continuity memory
- analyze `Monthly / Weekly -> Daily / 4H -> 1H -> 30m -> 15m -> 5m`
- decide bias, readiness, and levels
- update desired chart state and Discord summaries

What changes is only the delivery path for live market data.

## Runtime Split

The automation stack now has three separate responsibilities:

- `analysis layer`: the 8 scheduled Codex automations plus the paused manual
  live reassessment trigger
- `market runtime layer`: a local TradingView structured live-state reader plus
  watchdog
- `chart runtime layer`: a local executor plus watchdog

The Codex automations must no longer read TradingView directly during analysis.

Instead:

- the local market runtime reads TradingView live
- it writes structured live-state JSON
- the automations consume those local live-state files as their only live
  market source

## Source Of Truth For Live Reads

TradingView Structured Live State is now authoritative for live market context.

Primary files:

- [market_runtime/live_state/PEPPERSTONE_XAUUSD.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/live_state/PEPPERSTONE_XAUUSD.json)
- [market_runtime/live_state/FOREXCOM_US30.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/live_state/FOREXCOM_US30.json)
- [market_runtime/market_runtime_state.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/market_runtime_state.json)
- [market_runtime/market_watchdog_state.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/market_watchdog_state.json)

Deprecated compatibility mirror during transition:

- [market_runtime/snapshots/PEPPERSTONE_XAUUSD.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/snapshots/PEPPERSTONE_XAUUSD.json)
- [market_runtime/snapshots/FOREXCOM_US30.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/snapshots/FOREXCOM_US30.json)

That means:

- if an automation needs live context, it must read the live-state JSON first
- it must not call TradingView MCP tools directly in the analysis path
- it must not inspect, request, reference, or interpret screenshots / PNG files
  for trading decisions
- the valid market input is structured TradingView data:
  - `market.quote`
  - timeframe `state`
  - OHLCV bars
  - `M`, `W`, `D`, `4H`, `1H`, `30m`, `15m`, and `5m`
  - `derived_features` when available

## TradingView Structured Live State Contract

Each live-state file must remain valid JSON and should include:

```json
{
  "version": 2,
  "owned_by": "smart-money-good-money-tradingview-live-state",
  "state_version": 1,
  "updated_at": "2026-04-28T07:00:00-06:00",
  "updated_by": "tradingview_live_state_reader",
  "source_runtime": "SMART MONEY - GOOD MONEY Market Runtime",
  "source": "TradingView structured live state",
  "symbol": "PEPPERSTONE:XAUUSD",
  "status": "fresh",
  "as_of": "2026-04-28T07:00:00-06:00",
  "fresh_until": "2026-04-28T07:00:30-06:00",
  "freshness_seconds": 30,
  "data_mode": "structured_only",
  "timeframes_captured": ["M", "W", "D", "4H", "1H", "30m", "15m", "5m"],
  "market": {
    "info": {},
    "quote": {}
  },
  "timeframes": {
    "M": {},
    "W": {},
    "D": {},
    "4H": {},
    "1H": {},
    "30m": {},
    "15m": {},
    "5m": {}
  },
  "derived_features": {
    "liquidity": {},
    "reaction_zones": {},
    "volume_support": {},
    "price_action": {},
    "session_context": {},
    "risk_inputs": {},
    "timing_context": {}
  },
  "data_confidence": {
    "status": "FULL_DATA",
    "decision_allowed": true,
    "missing_fields": []
  },
  "visual_audit": {
    "enabled": false,
    "required_for_analysis": false
  },
  "last_error": null
}
```

Rules:

- `status` must be one of `fresh`, `stale`, or `degraded`
- `data_mode` must stay `structured_only`
- `market.quote` must exist for a symbol to be tradable
- `timeframes` must include `M`, `W`, `D`, `4H`, `1H`, `30m`, `15m`, and `5m`
- each required timeframe must include:
  - `timeframe`
  - `captured_at`
  - `state`
  - `bars`
  - `bar_count`
  - `latest_bar_time`
- raw structured data remains the source of truth
- `derived_features` are assessment aids only; they may be populated, partial,
  empty, `null`, or `unknown`
- `visual_audit` must never be required for trading analysis

## Data Confidence Contract

Valid market-data states:

- `FULL_DATA`
- `PARTIAL_DATA`
- `DATA_DEGRADED`

Rules:

- `FULL_DATA`
  - all required raw fields are valid
  - `decision_allowed = true`
- `PARTIAL_DATA`
  - required raw fields are valid
  - some non-critical derived feature remains unavailable or unknown
  - `decision_allowed = true`
- `DATA_DEGRADED`
  - required raw fields are missing or invalid
  - `decision_allowed = false`

Valid degradation reasons:

- stale or missing `as_of` / `fresh_until`
- missing `market.quote`
- missing `M / W / D / 4H / 1H / 30m / 15m / 5m` timeframe payloads
- empty `bars` for a required timeframe
- missing `latest_bar_time` for a required timeframe
- invalid JSON
- TradingView structured reader failure
- `TvGateway` failure that prevents structured data capture

Invalid degradation reasons:

- missing PNG
- missing screenshot path
- stale screenshot
- visual confidence limited
- VPA unavailable
- optional derived feature unknown

## Freshness Rule

- The maximum live-state age is `30 seconds`.
- If a symbol is older than that, it is no longer valid for automation
  analysis.
- Automations must not bypass this by calling TradingView directly.
- Normal per-symbol freshness is mandatory:
  - if `XAUUSD` is `FULL_DATA` and `US30` is `DATA_DEGRADED`, analyze XAUUSD
    and preserve US30
  - if `US30` is `FULL_DATA` and `XAUUSD` is `DATA_DEGRADED`, analyze US30 and
    preserve XAUUSD
  - if both are `FULL_DATA`, assess both normally
  - if both are `DATA_DEGRADED`, preserve both and finish degraded
- That normal per-symbol rule remains valid while the workflow is not stalled.
- After a formal workflow stall, the recovery gate depends on the workflow's
  required symbol set:
  - New York dual-symbol workflows require valid structured data for both
    `XAUUSD` and `US30` before the next full reassess + redraw
  - Asia gold workflows require valid structured data for `XAUUSD`; `US30`
    does not block the gold reassessment
- There is no all-or-nothing common screenshot window anymore.

## Stall And Recovery Contract

Treat `15 minutes` without a full valid structured assessment cycle as
`workflow_stalled`.

This is an operational recovery rule, not a trading signal.

The market runtime state now tracks:

- `last_full_valid_cycle_at`
- `workflow_stalled`
- `stall_started_at`
- `recovery_pending`
- `recovery_requested_at`
- `recovery_gate_status`
- `last_recovery_reassess_at`
- `valid_symbols`
- `invalid_symbols`
- `all_symbols_valid`

Rules:

- `workflow_stalled = true` means the old map should no longer be treated as a
  fresh operational baseline.
- `recovery_pending = true` means the runtime is waiting for the next valid
  reassessment cycle to acknowledge the stall.
- `recovery_gate_status = ready` means the required symbol set is valid again
  and the next eligible workflow should perform a full reassess + redraw.
- `recovery_gate_status = waiting_for_valid_symbols` means preserve prior maps
  and do not invent a fresh thesis yet.
- A recovery reassessment is acknowledged when desired-state files are refreshed
  after the recovery request.

## Symbol-Level Recovery Ladder

One symbol failure must not silently poison the other symbol's refresh result.

Each symbol capture now uses a short recovery ladder:

1. normal capture
2. immediate retry
3. re-select symbol/timeframe and retry
4. re-run gateway connection/status recovery
5. re-run the missing symbol only
6. if still broken, mark that symbol degraded and hold recovery

Recovery notes:

- degradation remains per symbol, not global by default
- missing screenshots do not count as structured-data failure
- only stale or missing structured fields, empty required bars, invalid JSON,
  TradingView reader failure, or gateway failure may degrade a symbol
- a healthy symbol should remain usable even when the other symbol is retrying

## Screenshots Are Outside The Trading-Analysis Contract

Screenshots are not part of the market-analysis contract.

- screenshots are not required
- screenshots are not interpreted
- screenshots do not affect `decision_allowed`
- screenshots do not affect `data_confidence`
- screenshots do not create `DATA_DEGRADED`
- screenshots do not block or delay the market assessment
- screenshots must never appear as the main reason for a trading decision

If debugging helpers keep screenshot capture in the codebase, they must remain
outside:

- `capture_symbol()`
- `capture_all()`
- `refresh_live_state_statuses()`
- `build_live_state_payload()`
- `validate_structured_data()`
- `data_confidence` calculation

## Derived Features For Reinforcement Support

The live-state payload may include these advisory blocks under
`derived_features`:

- `liquidity`
- `reaction_zones`
- `volume_support`
- `price_action`
- `session_context`
- `risk_inputs`
- `timing_context`

Rules:

- raw structured data remains the source of truth
- derived features must remain conservative and deterministic
- if a feature is not safely inferable, leave it `unknown`, `null`, `{}`, or
  `[]`
- derived features exist only to reinforce the existing strategy and the
  Articuno layer more consistently
- derived features must never create new trades
- derived features must never create new chart drawing types

What they support:

- liquidity precision
- level quality
- participation confirmation availability
- trigger quality
- New York opening context
- trade permission gating
- anti-chase timing discipline
- desired-state level-selection quality

## Market Snapshotter

The local live reader is:

- [market_snapshotter.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_snapshotter.py)

It:

- is the only live market reader that talks to TradingView directly
- captures quote plus structured OHLCV context for `D`, `4H`, `30m`, `15m`,
  and `5m`
- captures timeframe `state` together with OHLCV bars
- computes conservative derived features when deterministic
- writes a per-symbol live-state JSON
- writes a deprecated structured-only snapshot mirror during transition
- restores the prior chart symbol/timeframe after capture

## Market Watchdog

The watchdog is:

- [market_watchdog.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_watchdog.py)

Launcher:

- [start_market_watchdog.ps1](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_market_watchdog.ps1)

It:

- keeps the TradingView structured live-state reader alive outside Codex
  automations
- refreshes live-state JSON continuously
- records healthy / degraded cycles instead of waiting for manual rescue
- isolates symbol-level degradation so one bad symbol does not block the other
- mirrors stall and recovery readiness into watchdog state so workflows can see
  whether recovery is pending or ready before mutating desired state

## Shared TradingView Access Layer

The shared TradingView gateway is:

- [tv_gateway.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/tv_gateway.py)

It centralizes:

- `run_tv`
- `try_tv`
- modal dismissal
- connection recovery
- readiness checks
- a shared lock so the chart runtime and market runtime do not interleave
  TradingView commands

## Important Operating Assumption

The automation-owned chart layout remains a dedicated automation surface.

The market runtime may temporarily switch symbols and timeframes while capturing
structured live state, but it restores the prior chart state before releasing
the TradingView lock.
