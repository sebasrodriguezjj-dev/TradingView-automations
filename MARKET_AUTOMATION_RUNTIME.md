# Market Automation Runtime

## Goal

Keep the existing SMART MONEY - GOOD MONEY strategy intact while moving live
TradingView reads out of the Codex automation path.

The analytical workflows keep doing the same job:

- read continuity memory
- analyze `Daily / 4H -> 30m -> 15m -> 5m`
- decide bias, readiness, and levels
- update desired chart state and Discord summaries

What changes is only the delivery path for live market data.

## Runtime Split

The automation stack now has three separate responsibilities:

- `analysis layer`: the 8 scheduled Codex automations plus the paused manual
  live reassessment trigger
- `market runtime layer`: a local snapshotter plus watchdog
- `chart runtime layer`: a local executor plus watchdog

The Codex automations must no longer read TradingView directly during analysis.

Instead:

- the local market runtime reads TradingView live
- it writes fresh local snapshots plus screenshots
- the automations consume those snapshot files as their live market source

## Source Of Truth For Live Reads

For live market context, the snapshot files are now authoritative.

Current files:

- [market_runtime/snapshots/PEPPERSTONE_XAUUSD.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/snapshots/PEPPERSTONE_XAUUSD.json)
- [market_runtime/snapshots/FOREXCOM_US30.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/snapshots/FOREXCOM_US30.json)

That means:

- if an automation needs live context, it should read the snapshot JSON first
- if it needs visual confirmation, it should read the market-runtime screenshots
- it must not call TradingView MCP tools directly in the analysis path
- the structured snapshot JSON is the primary trading input
- screenshots are a supporting confirmation layer, not the primary gate for whether the workflow may produce a market assessment

## Snapshot Contract

Each snapshot file must remain valid JSON and should include:

```json
{
  "version": 1,
  "owned_by": "smart-money-good-money-market-runtime",
  "state_version": 1,
  "updated_at": "2026-04-23T07:00:00-06:00",
  "updated_by": "market_snapshotter",
  "source_runtime": "SMART MONEY - GOOD MONEY Market Runtime",
  "symbol": "PEPPERSTONE:XAUUSD",
  "status": "fresh",
  "as_of": "2026-04-23T07:00:00-06:00",
  "fresh_until": "2026-04-23T07:00:30-06:00",
  "freshness_seconds": 30,
  "visual_mode": "data + screenshots",
  "timeframes_captured": ["D", "4H", "30m", "15m", "5m"],
  "screenshots": {},
  "market": {},
  "timeframes": {},
  "last_error": null
}
```

Rules:

- `status` must be one of `fresh`, `stale`, or `degraded`
- `fresh_until` defines the maximum acceptable age for automation analysis
- `market.quote` should reflect the current live quote
- `timeframes` should include `D`, `4H`, `30m`, `15m`, and `5m`
- `screenshots` should normally include a fresh `5m` capture and retain the
  latest available `4H`, `30m`, and `15m` context captures
- if the JSON snapshot is fresh and includes valid `quote + timeframes`, the
  workflow may still produce a live market assessment even if one or more
  screenshots are missing or older than ideal
- missing screenshots should reduce visual confidence, not automatically block
  the trading assessment

## Freshness Rule

- The snapshot maximum age is `30 seconds`.
- If the structured JSON snapshot is older than that, it is no longer valid for
  automation analysis.
- The `5m` screenshot is refreshed every live capture cycle.
- `15m`, `30m`, and `4H` screenshots are refreshed opportunistically so the
  runtime can keep the per-symbol market snapshot inside the `30 seconds`
  freshness window without reintroducing manual prompts.
- Automations must not bypass this by calling TradingView directly.
- Degrade only when the structured trading data is no longer trustworthy:
  - stale or missing `as_of` / `fresh_until`
  - missing `market.quote`
  - missing critical `D / 4H / 30m / 15m / 5m` timeframe payloads
- If the JSON snapshot is fresh but screenshots are missing or stale:
  - continue the market assessment using the JSON snapshot as primary truth
  - mention the screenshot limitation only as a secondary confidence note when
    it materially matters
  - do not turn the whole workflow into a runtime-health report
- If a needed structured snapshot is stale or degraded:
  - wait briefly for the runtime to refresh it
  - if it still fails to refresh, finish in `STALE SNAPSHOT / DEGRADED`
  - do not block on manual approval prompts

## Market Snapshotter

The local market reader is:

- [market_snapshotter.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_snapshotter.py)

It:

- is the only live market reader that talks to TradingView directly
- captures quote plus OHLCV context for `D`, `4H`, `30m`, `15m`, and `5m`
- captures screenshots for `4H`, `30m`, `15m`, and `5m`
- restores the prior chart symbol/timeframe after capture
- writes a per-symbol snapshot JSON

## Market Watchdog

The watchdog is:

- [market_watchdog.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_watchdog.py)

Launcher:

- [start_market_watchdog.ps1](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_market_watchdog.ps1)

It:

- keeps the market snapshotter alive outside Codex automations
- refreshes snapshots continuously
- records degraded cycles instead of waiting for manual rescue

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
its snapshots, but it restores the prior chart state before releasing the
TradingView lock.
