# Chart Automation Runtime

## Goal

Keep the existing SMART MONEY - GOOD MONEY strategy intact while moving chart
writes out of the Codex automation path.

The analytical workflows keep doing the same job:

- read continuity memory
- analyze `Daily / 4H -> 30m -> 15m -> 5m`
- decide bias, readiness, and levels
- write Discord summaries

What changes is only the delivery path for chart markings.

## Runtime Split

The automation stack now has three separate responsibilities:

- `analysis layer`: the 8 Codex automations plus the paused manual live
  reassessment trigger
- `market runtime layer`: a local snapshotter plus watchdog
- `chart runtime layer`: a local executor plus watchdog

The Codex automations must no longer be the direct writer of TradingView drawings.

Instead:

- automations read live market context from the market-runtime snapshot files
- automations update the desired chart state JSON files
- the local chart executor watches those files
- the executor is the only writer of automation-owned chart drawings
- the watchdog keeps the executor alive and records failures

Related live-read contract:

- [MARKET_AUTOMATION_RUNTIME.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/MARKET_AUTOMATION_RUNTIME.md)

## Source Of Truth

For automation-owned chart markings, the desired state files are now authoritative.

Current files:

- [chart_runtime/desired_states/PEPPERSTONE_XAUUSD.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/desired_states/PEPPERSTONE_XAUUSD.json)
- [chart_runtime/desired_states/FOREXCOM_US30.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/desired_states/FOREXCOM_US30.json)

That means:

- if the chart and the desired state disagree, the desired state wins
- the current TradingView drawing layer is only a rendered view, not the durable memory layer
- continuity still lives in:
  - [SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md)

## Ownership Boundary

The chart runtime owns:

- `4H SUPPORT`
- `4H RESISTANCE`
- `5M EXECUTION LONG`
- `5M EXECUTION SHORT`
- line-only entry markup: `ENTRY`, `TP1`, `TP2`, `TP3`, `SL`

The chart runtime does not change strategy logic. It only renders the state the workflows decide.

## Rendering Contract

- `HTF` levels remain infinite horizontal lines.
- `5m` execution levels remain short finite lines.
- Entry markup remains line-only and compact.
- Every owned level renders as a clean line plus a separate right-side text label.
- The runtime must not leave text embedded over active candles.
- `HTF` and `5m` are separate layers even if the executor uses a full redraw of the automation-owned map.
- Colors follow:
  - `4H SUPPORT`: green
  - `4H RESISTANCE`: red
  - `5M EXECUTION LONG`: blue
  - `5M EXECUTION SHORT`: yellow
  - `ENTRY`: blue
  - `SL`: red
  - `TP1`, `TP2`, `TP3`: green

## Desired State Contract

Each symbol state file must remain valid JSON and should include:

```json
{
  "version": 1,
  "owned_by": "smart-money-good-money-chart-runtime",
  "state_version": 1,
  "updated_at": "2026-04-21T14:35:00-06:00",
  "updated_by": "workflow-or-manual-source",
  "source_workflow": "mid-session-reassessment",
  "symbol": "PEPPERSTONE:XAUUSD",
  "timeframe": "5",
  "session": "NY",
  "thesis_state": "BOUNCE INTO SUPPLY / SHORT HUNT",
  "action_state": "LOOK FOR SHORTS ON REJECTION",
  "cleanup_scope": "5m_only",
  "apply_mode": "full_symbol_redraw",
  "risk_model": {
    "unit": "pips",
    "tp1": 60,
    "tp2": 80,
    "tp3": 100,
    "sl_preferred_min": 60,
    "sl_preferred_max": 80,
    "sl_hard_max": 100
  },
  "levels": {
    "htf": [],
    "execution_5m": [],
    "trade_entry": []
  }
}
```

Rules:

- `htf` should usually keep a meaningful `4H SUPPORT` / `4H RESISTANCE` pair when both still matter.
- `execution_5m` should usually keep one active `5M EXECUTION LONG` and one active `5M EXECUTION SHORT`.
- `trade_entry` is optional and only used when there is a confirmed trade markup to preserve.
- If a workflow has no reason to modify a symbol, it should leave that symbol file untouched.
- If a workflow invalidates the old `5m` pair, it should overwrite the `execution_5m` block with the new active pair instead of stacking generations.
- If a workflow performs a full reassessment, the resulting desired state must describe the entire automation-owned map for that symbol, not only the delta.

## Workflow Permissions

Keep this ownership model:

- `NY Open Levels`
  - may set or refresh HTF + 5m baseline for `XAUUSD` and `US30`
- `Post Open Validation`
  - may refresh `5m`
  - may adjust HTF only if structure clearly changed
- `Active Setup Detector`
  - may refresh `5m`
  - may add entry markup if a concrete trade is confirmed
- `Bias Integrity Check`
  - may invalidate or refresh `5m`
  - may remove one side of HTF only if the HTF thesis truly failed
- `Mid-Session Reassessment`
  - may replace the active `5m` pair
  - may revise HTF if the higher-timeframe thesis itself changed
- `End-of-Day Review`
  - must not mutate desired chart state
- `Asia Session Gold`
  - may set or refresh HTF + 5m baseline for `XAUUSD`
- `Asia Setup Detector`
  - may refresh `5m`
  - may add entry markup if a concrete trade is confirmed

## Executor Behavior

The executor is:

- [chart_executor.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_executor.py)

It:

- reads desired state files
- skips unchanged states
- sets symbol + timeframe
- clears the automation-owned drawing layer by full redraw
- redraws HTF, 5m, and optional entry markup from desired state
- verifies the owned drawing layer was actually cleared before rebuilding
- captures a verification screenshot
- records applied state and runtime health

### Reassessment Safety Rule

If a reassessment or manual live trigger updates the active `5m` pair:

- the runtime must fully clear the owned drawing layer for that symbol
- the runtime must rebuild only the levels that still exist in desired state
- the runtime must not let duplicate execution generations survive
- the runtime must not leave legacy label text interposed over active candles
- verification should treat `1 line + 1 right-side label per owned level` as the clean target state

### Why Full Redraw

The current TradingView CLI path has been unreliable for targeted drawing introspection/removal in some runs.

So the runtime uses a pragmatic rule:

- treat the automation-owned chart layer as fully declarative
- when desired state changes, redraw the owned layer cleanly from the new state

That is how we avoid stale `5m` lines surviving just because targeted delete broke.

## Watchdog

The watchdog is:

- [chart_watchdog.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_watchdog.py)

Launcher:

- [start_chart_watchdog.ps1](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_chart_watchdog.ps1)

It:

- runs the executor loop outside Codex automations
- records failures
- keeps retrying on the next poll

## Shared TradingView Gateway

Both runtimes now use the same TradingView access layer:

- [tv_gateway.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/tv_gateway.py)

That gateway owns:

- direct `tv` CLI invocation
- modal dismissal
- connection recovery
- symbol/timeframe readiness checks
- a shared lock so live reads and chart writes do not interleave

## Runtime Outputs

Runtime artifacts:

- applied states:
  - [chart_runtime/applied_states](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/applied_states)
- screenshots:
  - [chart_runtime/screenshots](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/screenshots)
- executor health:
  - [chart_runtime/chart_runtime_state.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/chart_runtime_state.json)
- watchdog health:
  - [chart_runtime/chart_watchdog_state.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/chart_watchdog_state.json)

## Important Operating Assumption

The automation-owned layout should be treated as a dedicated automation surface.

Do not rely on unmanaged discretionary drawings surviving inside the same automation-owned chart layer.

If you want a manual discretionary layout, keep it separate from the automation runtime layout.
