# Workflow Marking Rules

Use these rules as mandatory workflow logic for chart markings, execution-line lifecycle, and decision freshness.

Supporting refinement references:

- [ARTICUNO_REINFORCEMENT_LAYER.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/ARTICUNO_REINFORCEMENT_LAYER.md)
- [TRANSCRIPT_COMPATIBILITY_MATRIX.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/TRANSCRIPT_COMPATIBILITY_MATRIX.md)
- [ENTRY_TIMING_ADDENDUM.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/ENTRY_TIMING_ADDENDUM.md)

## Core Intent

- Preserve higher-timeframe continuity without letting old 5m execution markings dominate the chart after structure has moved on.
- Keep the chart readable at a glance.
- Keep labels visually anchored to the current right side of the chart on every workflow run.
- Keep the final trading decision aligned with both higher-timeframe thesis and current execution readiness.

## Runtime Ownership

- Codex automations remain the analysis layer. They decide what the chart should contain.
- Codex automations must consume live market context from the local market-runtime structured live-state JSON, not from direct TradingView MCP tool calls.
- The local chart runtime is now the only writer of automation-owned TradingView drawings.
- The local market runtime is now the only live reader that talks to TradingView directly for automation analysis.
- Automations must update the desired state JSON files instead of relying on direct chart drawing or removal actions.
- The desired state files are authoritative for automation-owned markings. The rendered TradingView chart is a view of that state, not the durable source of truth.
- The runtime contract is documented in:
  - [CHART_AUTOMATION_RUNTIME.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/CHART_AUTOMATION_RUNTIME.md)
  - [MARKET_AUTOMATION_RUNTIME.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/MARKET_AUTOMATION_RUNTIME.md)

## Label Repositioning

- On every new workflow run, move every active label or tag for preserved levels back to the current right side of the chart.
- Do not leave labels stranded over older candles just because time passed.
- If a level is preserved, refresh the label position even when the price level itself is unchanged.
- If a level is removed, remove its label too.
- If duplicate labels or duplicate lines exist for the same semantic level, keep one clean active version and remove the rest.
- Do not embed level text directly on top of active candles when a separate right-side label can be rendered instead.

## Color Standard

Never allow gray or default-neutral colors when a semantic color is available.

Use this palette consistently:

- `4H SUPPORT`: green
- `4H RESISTANCE`: red
- `5M EXECUTION LONG`: blue
- `5M EXECUTION SHORT`: yellow
- `PDH`: red
- `PDL`: green
- `ON HIGH`: amber
- `ON LOW`: teal
- `RANGE HIGH`: amber
- `RANGE LOW`: teal
- `ENTRY` divider: blue
- `SL`: red
- `TP1`, `TP2`, `TP3`: green

Execution-side convention:

- long-side execution lines are blue
- short-side execution lines are yellow

## Higher-Timeframe Line Standard

- The HTF manual layer should normally preserve a structural pair per symbol: at least one `4H SUPPORT` and one `4H RESISTANCE` whenever both remain meaningful.
- Higher-timeframe manual levels such as `4H SUPPORT` and `4H RESISTANCE` must be drawn as infinite horizontal lines.
- 5m execution lines must remain short and finite so they are visually distinct from the HTF layer.

## Entry Markup Standard

- Default entry markup is `ENTRY + TP1 + TP2 + TP3 + SL` using short, finite, bounded horizontal lines only.
- Do not draw risk/reward rectangles by default.
- Every execution line must stay visually short and compact near the active setup area.
- Every execution line must have its label on the right side.
- `ENTRY` must be shown as its own labeled line unless the user explicitly says not to include it.
- `BE` is optional and should only appear when relevant.
- If a line-based entry markup becomes cluttered, duplicated, or too wide, rebuild it immediately in the short-line format.

## Entry Risk Model

- Proposed entries must fit the user's risk model before they are considered valid.
- Default target ladder is `TP1 = 60`, `TP2 = 80`, `TP3 = 100` in the native risk unit of the symbol.
- Preferred stop range is usually `60-80`; `100` is the hard ceiling and should be used only when the context offers better `RR`.
- If the structural invalidation requires more than the allowed risk budget, do not force the setup; refine the entry or reject it.

## 5m Execution Lifecycle

Treat higher-timeframe thesis and 5m execution as separate states.

- A Daily / 4H idea may remain valid while the old 5m execution line is no longer tradable.
- Before preserving a 5m execution line, classify it as `ACTIVE`, `STALE`, or `INVALIDATED`.

Definitions:

- `ACTIVE`: still near current price and still structurally usable.
- `STALE`: still informative, but too far from current price, already chased, or no longer the cleanest trigger.
- `INVALIDATED`: clearly broken, accepted through, mitigated too many times, or replaced by a cleaner trigger.

Rules:

- Remove `INVALIDATED` 5m execution lines from the chart.
- Remove or demote `STALE` 5m execution lines unless they still matter as invalidation or context.
- Do not let `STALE` 5m lines dominate the decision.
- Never keep an old 5m execution line as the active trade idea if the chart has materially moved on and a new cleaner trigger exists closer to price.
- Prefer one primary active `5M EXECUTION LONG` and one primary active `5M EXECUTION SHORT` per symbol unless an older level still matters as invalidation or structural reference.
- When a new active 5m pair is promoted, remove the obsolete old 5m pair instead of letting both pairs coexist.
- That hard cleanup applies to the 5m execution map only, not to preserved higher-timeframe manual levels.

## Decision Freshness

The final action state must reflect both:

- higher-timeframe thesis
- current execution readiness

That means:

- If the higher-timeframe bias is still valid but the execution line is `STALE`, the correct decision is `WAIT` or `NO CLEAR EDGE`.
- Do not keep repeating an old `VALID LONG SETUP` or `VALID SHORT SETUP` just because the higher-timeframe thesis is still alive.
- A setup is only active if the execution trigger is still structurally valid and still close enough to current price to be actionable.
- Use the Entry & Timing Addendum to separate `indication`, `correction`, and `continuation` instead of treating the first impulse as automatic execution.
- Prefer confirmation after correction over chasing the first expansion candle.

## Opportunity Timing State

Every reassessment must classify the current opportunity timing, not just the structural levels.

Required timing states:

- `PRE-TRIGGER`: the idea exists, but price has not reached the trigger shelf or still lacks the rejection / reclaim that activates it.
- `ARMED`: price is in the trigger zone and one more confirmation can activate the setup.
- `TRIGGERED`: the trigger already happened and the move is already active or already left the intended entry area.
- `EXPIRED`: the idea already played out too far, failed structurally, or no longer offers the intended execution quality.

Rules:

- Do not keep saying `WAIT for retest` if the retest already happened and rejected cleanly; that setup is `TRIGGERED`, not `WAIT`.
- Do not keep calling a setup fresh if price already traveled too far from the intended trigger. Classify it as `EXPIRED` or `POST-TRIGGER / WAIT FOR NEW RETEST`.
- If a setup is `TRIGGERED`, explicitly state whether the correct action is:
  - `manage if already in`
  - `do not chase`
  - `wait for new retest`
- If a setup is `ARMED`, explicitly state:
  - what exact trigger is still missing
  - what price level flips it to `TRIGGERED`
- Record the timing state together with the usual `ACTIVE / STALE / INVALIDATED` classification for the `5m` pair.
- Use `15m` as the minimum setup-quality filter and `5m` as execution only; do not let isolated `5m` noise promote a setup without the intended `30m/15m` support.
- Use simple structure language when possible: `HH/HL`, `LH/LL`, swing high, swing low, break, reclaim, rejection.

## Chart Actions Standard

When preserving or updating levels:

- Update the desired chart state first. Do not depend on direct chart clicks from inside the automation run.
- Treat every reassessment as a declarative redraw of the automation-owned layer, not as a partial cosmetic tweak.
- Preserve relevant 4H levels unless structure clearly invalidates them.
- Treat preserved 4H levels as infinite HTF structure, not as short execution segments.
- Re-anchor all kept labels to the current right side of the chart.
- Remove duplicate labels and duplicate lines.
- Force the explicit color palette above.
- Remove invalidated 5m execution lines.
- Remove or demote stale 5m execution lines if they no longer help execution.
- Add a new 5m execution line only when a cleaner and more current trigger truly exists.
- If the task is only to refresh 5m entries, do not wipe the HTF layer while cleaning the old 5m pair.
- When the user confirms an entry, mark the trade with short bounded lines for `ENTRY`, `TP1`, `TP2`, `TP3`, and `SL` rather than boxes.

## Articuno Chart-Marking Reinforcement

- Articuno does not change the drawing vocabulary of the engine.
- Articuno only improves:
  - level selection
  - level lifecycle classification
  - whether a level is `ACTIVE`, `STALE`, or `INVALIDATED`
  - whether trade markup is permitted by risk
  - whether `desired_state` should be preserved, refreshed, simplified, or left untouched
- Before updating `desired_state`, use Articuno only to ask whether the current `4H SUPPORT`, `4H RESISTANCE`, `5M EXECUTION LONG`, or `5M EXECUTION SHORT` still have real structural and liquidity quality.
- Articuno may reinforce whether `ENTRY / SL / TP1 / TP2 / TP3` markup is allowed, but only through the existing risk model.
- Do not mark random micro pivots as execution levels.
- Do not draw fresh entry levels after liquidity has already been paid.
- Do not repackage a late setup as a fresh desired-state update.
- Do not add new shapes, boxes, OB zones, FVG zones, trendline systems, or indicator drawings.
- Keep HTF infinite.
- Keep 5m finite.
- Keep semantic colors unchanged.
- Keep `desired_state` authoritative.

## Reassessment Redraw Standard

When a workflow or manual trigger performs a full reassessment:

- Re-read continuity memory, marking rules, and desired state before deciding whether the old 5m pair is still `ACTIVE`, has become `STALE`, or is `INVALIDATED`.
- If the active 5m pair changed, fully clear the automation-owned drawing layer and rebuild it from desired state instead of stacking generations.
- The rebuilt owned layer should contain only:
  - the preserved HTF pair
  - the current active 5m pair
  - optional current trade-entry markup if there is an active user-confirmed trade
- After rebuild, there should be exactly one clean line and one clean right-side label per owned level.
- If visual verification shows duplicate execution lines, duplicate labels, or interposed text, the reassessment is not complete and the runtime must rebuild again.
- Never let `ON HIGH`, `ON LOW`, `PDH`, `PDL`, old trade-entry marks, or earlier 5m generations survive a reassessment unless they are explicitly present in desired state for that symbol.

## Shared Memory Update Standard

When updating `SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md`, explicitly record:

- which 5m execution lines remained `ACTIVE`
- which became `STALE`
- which were `INVALIDATED`
- what the opportunity timing state was: `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED`
- whether the read used a transcript-derived refinement rule or coaching note from the compatibility matrix / timing addendum
- which labels were repositioned
- which levels were recolored, removed, or replaced

## Failure Handling

- If a newly created or preserved markup does not visually match these rules, do not keep it just because it exists.
- Fix it immediately, or remove it and rebuild it cleanly.
- Direct TradingView MCP tool calls are forbidden in the automation analysis path.
- If a required market live-state file is stale or `DATA_DEGRADED`, do not bypass it with a direct live read from inside the automation. Wait briefly for the local market runtime to refresh it, then preserve the prior map for that symbol if it still fails.
- If a chart action fails during analysis, do not leave the workflow blocked waiting for a human. Update the desired state, let the local runtime reconcile the chart, and record the failure in continuity memory if it matters.

## Structured Live State Rule

- Use `market_runtime/live_state/*.json` as the only live market input for analysis.
- Do not inspect, request, reference, or interpret screenshots / PNG files for trading decisions.
- Required live structured inputs are:
  - `market.quote`
  - timeframe `state`
  - OHLCV bars
  - `D`, `4H`, `30m`, `15m`, and `5m`
  - `derived_features` when available
- If one symbol is `FULL_DATA` and the other is `DATA_DEGRADED`, analyze the fresh symbol and preserve the degraded symbol.
- If both symbols are `DATA_DEGRADED`, preserve prior maps and do not invent new setup decisions.
