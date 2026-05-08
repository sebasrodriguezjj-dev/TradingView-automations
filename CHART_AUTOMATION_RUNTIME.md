# Chart Automation Runtime

## Goal

Keep the existing SMART MONEY - GOOD MONEY strategy intact while moving chart
writes out of the Codex automation path.

The analytical workflows keep doing the same job:

- read continuity memory
- analyze `Monthly / Weekly -> Daily / 4H -> 1H -> 30m -> 15m -> 5m`
- decide bias, readiness, and levels
- write Discord summaries

What changes is only the delivery path for chart markings.

## Runtime Split

The automation stack now has three separate responsibilities:

- `analysis layer`: the 8 Codex automations plus the paused manual live
  reassessment trigger
- `market runtime layer`: a local TradingView structured live-state reader plus watchdog
- `chart runtime layer`: a local executor plus watchdog

The Codex automations must no longer be the direct writer of TradingView drawings.

Instead:

- automations read live market context from the market-runtime live-state files
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

- `DAILY SUPPLY`
- `DAILY DEMAND`
- `MONTHLY SUPPLY`
- `MONTHLY DEMAND`
- `WEEKLY SUPPLY`
- `WEEKLY DEMAND`
- `4H DEMAND`
- `4H SUPPLY`
- `1H SUPPLY`
- `1H DEMAND`
- `5M EXECUTION LONG`
- `5M EXECUTION SHORT`
- `CHART NOTE` as a planning-only, pre-permission visual exception
- line-only entry markup: `ENTRY`, `TP1`, `TP2`, `TP3`, `SL`

The chart runtime does not change strategy logic. It only renders the state the workflows decide.

## Rendering Contract

- Embedded centered line text is a hard rule for both automation-owned charts: `PEPPERSTONE:XAUUSD` and `FOREXCOM:US30`.
- Macro, `Daily`, `4H`, and `1H` context / structure levels now live inside the existing preserved HTF layer.
- `HTF` levels remain infinite horizontal lines.
- `5m` execution levels remain execution-only, but they now render as endless horizontal lines from left to right.
- Entry markup remains line-only and compact.
- `CHART NOTE` is the only approved planning-only exception to the drawing
  vocabulary. It is a lightweight standalone note, not executable trade markup.
- Every owned level renders as one clean line with its text embedded in the line itself.
- Embedded line text must be centered in the line, not floated separately on the right side.
- `HTF` and `5m` are separate layers even if the executor uses a full redraw of the automation-owned map.
- `Monthly` and `Weekly` remain macro context-only and must never be treated as execution triggers by themselves.
- `Daily` remains context-only and must never be treated as an execution trigger by itself.
- `4H` remains the structural HTF layer.
- `1H` remains tactical correlation and must never replace `30m`, `15m`, or `5m` execution maturity.
- `5m` remains execution-only and must render as a real endless horizontal line, not a text-only artifact.
- Automation-owned chart lines and labels must remain savable and editable on the TradingView chart.
- The executor must never create automation-owned shapes with flags that disable saving or editing.
- Colors follow:
  - `MONTHLY SUPPLY`: violet
  - `MONTHLY DEMAND`: cyan
  - `WEEKLY SUPPLY`: light purple
  - `WEEKLY DEMAND`: aqua
  - `DAILY SUPPLY`: purple
  - `DAILY DEMAND`: teal
  - `4H DEMAND`: green
  - `4H SUPPLY`: red
  - `1H SUPPLY`: rose
  - `1H DEMAND`: mint
  - `5M EXECUTION LONG`: blue
  - `5M EXECUTION SHORT`: yellow
  - `CHART NOTE`: amber
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
  "refresh_reason": "manual_reassessment",
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
    "htf": [
      {
        "label": "DAILY SUPPLY 4730.08",
        "semantic": "DAILY SUPPLY",
        "price": 4730.08,
        "style": "infinite",
        "enabled": true
      },
      {
        "label": "DAILY DEMAND 4667.18",
        "semantic": "DAILY DEMAND",
        "price": 4667.18,
        "style": "infinite",
        "enabled": true
      },
      {
        "label": "4H SUPPLY 4772.95",
        "semantic": "4H SUPPLY",
        "price": 4772.95,
        "style": "infinite",
        "enabled": true
      },
      {
        "label": "4H DEMAND 4554.76",
        "semantic": "4H DEMAND",
        "price": 4554.76,
        "style": "infinite",
        "enabled": true
      }
    ],
    "execution_5m": [],
    "trade_entry": [],
    "chart_note": []
  }
}
```

Rules:

- `htf` may now contain active `MONTHLY SUPPLY`, `MONTHLY DEMAND`, `WEEKLY SUPPLY`, `WEEKLY DEMAND`, `DAILY SUPPLY`, `DAILY DEMAND`, `4H DEMAND`, `4H SUPPLY`, `1H SUPPLY`, and `1H DEMAND` when they still matter.
- `Monthly` and `Weekly` live inside the preserved HTF context layer and remain macro context-only.
- `Daily` lives inside the preserved HTF context layer and remains context-only.
- `4H` remains the structural HTF layer inside the same `htf` array.
- `1H` remains tactical correlation inside the same `htf` array; include it only when it clarifies acceptance, rejection, or transition.
- `execution_5m` should usually keep one active `5M EXECUTION LONG` and one active `5M EXECUTION SHORT`.
- `execution_5m` is still execution-only logically, but its chart directive is now fixed to endless horizontal lines from left to right.
- `chart_note` is optional and planning-only. It may be used before trade
  permission exists, but it must never be confused with a live entry.
- `trade_entry` is optional and only used when there is a confirmed trade markup to preserve.
- `refresh_reason` should be written when a workflow mutates desired state:
  - `stall_recovery`
  - `5m_far_from_price`
  - `htf_changed`
  - `manual_reassessment`
- If a workflow has no reason to modify a symbol, it should leave that symbol file untouched.
- If a workflow invalidates the old `5m` pair, it should overwrite the `execution_5m` block with the new active pair instead of stacking generations.
- `cleanup_scope = "5m_only"` may clean only `execution_5m`, `trade_entry`, and short-lived `chart_note` objects; it must not remove Monthly, Weekly, Daily, 4H, or useful 1H levels preserved in `levels.htf`.
- If a workflow performs a full reassessment, the resulting desired state must describe the entire automation-owned map for that symbol, not only the delta.
- `CHART NOTE` must disappear when:
  - a real `ENTRY / SL / TP1 / TP2 / TP3` map is permitted
  - the idea expires
  - the workflow refreshes away from that setup

## Workflow Permissions

Keep this ownership model:

- `NY Open Levels`
  - must set or refresh the baseline `Daily` pair, `4H` pair, and `5m` pair for `XAUUSD` and `US30`
- `Post Open Validation`
  - may refresh `5m`
  - may preserve or refresh `Daily` only if the higher-timeframe thesis clearly changed
  - may adjust `4H` only if structure clearly changed
- `Active Setup Detector`
  - should preserve the `Daily` pair unless the HTF context is clearly stale
  - may refresh `5m`
  - may add a `CHART NOTE` before risk permission exists
  - may add entry markup if a concrete trade is confirmed
- `Bias Integrity Check`
  - may preserve or refresh `Daily` only if higher-timeframe integrity clearly changed
  - may invalidate or refresh `5m`
  - may remove one side of HTF only if the HTF thesis truly failed
- `Mid-Session Reassessment`
  - may replace the active `5m` pair
  - may revise `Daily` and `4H` only if the higher-timeframe thesis itself changed
  - may add, preserve, or remove a `CHART NOTE` as planning context
- `End-of-Day Review`
  - must not mutate desired chart state
- `Asia Session Gold`
  - must set or refresh the baseline `Daily` pair, `4H` pair, and `5m` pair for `XAUUSD`
- `Asia Setup Detector`
  - should preserve the `Daily` pair unless the HTF context is clearly stale
  - may refresh `5m`
  - may add a `CHART NOTE` before risk permission exists
  - may add entry markup if a concrete trade is confirmed

## Executor Behavior

The executor is:

- [chart_executor.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_executor.py)

It:

- reads desired state files
- skips unchanged states
- sets symbol + timeframe
- clears the automation-owned drawing layer by full redraw
- redraws `Daily`, `4H`, `5m`, and optional entry markup from desired state
- redraws optional `CHART NOTE` context from desired state
- uses the native TradingView chart API path so `Daily`, `4H`, and `5m` levels all render as real horizontal lines, while trade-entry markup can remain finite when present
- verifies the owned drawing layer was actually cleared before rebuilding
- verifies the final owned shape count matches `1 line with embedded text`
  per enabled owned level, plus one note shape per enabled `CHART NOTE`
- rejects any automation-owned shape payload that tries to reintroduce non-editable or non-savable flags
- captures a verification screenshot for render verification only
- records applied state and runtime health

### Reassessment Safety Rule

If a reassessment or manual live trigger updates the active `5m` pair:

- the runtime must fully clear the owned drawing layer for that symbol
- the runtime must rebuild only the levels that still exist in desired state
- the runtime must not let duplicate execution generations survive
- the runtime must not leave legacy detached label text interposed over active candles
- the runtime must not accept a redraw where labels appear but the `5m` lines themselves failed to render as endless horizontal lines
- verification should treat `1 line with embedded centered text per owned level` as
  the clean target state, plus only the explicitly requested `CHART NOTE`

## Reassess And Redraw Triggers

The chart runtime does not invent new structure by itself, but it must respond
cleanly when workflows declare a refresh.

Required workflow-side refresh triggers:

- `stall_recovery`
  - use after a formal workflow stall once the required symbol set is valid
  - perform a full reassess + redraw
- `5m_far_from_price`
  - use when both active `5m` execution levels are structurally behind price
    and no longer define execution readiness
  - replace the stale pair instead of preserving dead execution lines
- `htf_changed`
  - use only when `Daily / 4H` structure materially changed
- `manual_reassessment`
  - use for an intentional user-driven refresh

HTF rule:

- `Daily / 4H` must be re-evaluated every live cycle
- HTF lines should be redrawn only when higher-timeframe structure materially
  changed
- if HTF is unchanged, preserve HTF and refresh only the execution layer when
  needed

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

## Render Verification Boundary

- Chart-runtime screenshots are render verification only.
- They are not market data.
- They are not a trading-analysis input.
- They must not affect market `data_confidence`.
- They may support `CHART_RENDER_DEGRADED` logging, but they must not change
  the trading thesis or block a live market assessment that already has
  `FULL_DATA` or `PARTIAL_DATA`.
