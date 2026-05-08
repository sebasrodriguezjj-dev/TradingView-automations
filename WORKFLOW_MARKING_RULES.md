# Workflow Marking Rules

Use these rules as mandatory workflow logic for chart markings, execution-line lifecycle, and decision freshness.

Supporting refinement references:

- [ARTICUNO_REINFORCEMENT_LAYER.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/ARTICUNO_REINFORCEMENT_LAYER.md)
- [TRANSCRIPT_COMPATIBILITY_MATRIX.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/TRANSCRIPT_COMPATIBILITY_MATRIX.md)
- [ENTRY_TIMING_ADDENDUM.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/ENTRY_TIMING_ADDENDUM.md)

## Core Intent

- Preserve higher-timeframe continuity without letting old 5m execution markings dominate the chart after structure has moved on.
- Keep the chart readable at a glance.
- Keep automation-owned line text visually centered inside the line on every workflow run.
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

## Workflow Stall Recovery

Treat `15 minutes` without a full valid structured assessment cycle as
`workflow_stalled`.

Rules:

- `workflow_stalled` is operational only. It does not change strategy.
- While a workflow is stalled, do not keep pretending the old execution map is
  still a fresh operational map.
- For New York dual-symbol workflows, a recovery reassess + redraw requires
  valid structured data for both `XAUUSD` and `US30`.
- For Asia gold workflows, `XAUUSD` is the required symbol set; `US30` does not
  block the reassessment.
- `End-of-Day Review` never mutates chart state and never triggers chart
  recovery behavior.
- If recovery is pending and the required symbol set is not valid yet, preserve
  prior maps and report `recovery pending` instead of inventing a new thesis.

## Embedded Line Text

- This is a hard rule for both automation-owned workflow charts: `PEPPERSTONE:XAUUSD` and `FOREXCOM:US30`.
- This hard rule applies on every automation cycle, manual reassessment, and runtime redraw.
- On every new workflow run, keep the text for automation-owned line draws embedded in the line itself instead of rendering a separate right-side label.
- The text for `MONTHLY`, `WEEKLY`, `DAILY`, `4H`, `1H`, `5M`, and line-based trade-entry draws must sit in the center of the line.
- If a level is preserved, refresh the line so the embedded text remains attached to the active line instance.
- If a level is removed, remove its embedded text with the line.
- If duplicate text or duplicate lines exist for the same semantic level, keep one clean active version and remove the rest.
- Do not let embedded line text drift over active candles if a cleaner line-centered placement is available through redraw.

## Color Standard

Never allow gray or default-neutral colors when a semantic color is available.

Use this palette consistently:

- `DAILY SUPPLY`: purple
- `DAILY DEMAND`: teal
- `4H DEMAND`: green
- `4H SUPPLY`: red
- `MONTHLY SUPPLY`: violet
- `MONTHLY DEMAND`: cyan
- `WEEKLY SUPPLY`: light purple
- `WEEKLY DEMAND`: aqua
- `1H SUPPLY`: rose
- `1H DEMAND`: mint
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

- The HTF manual layer should normally preserve meaningful macro, Daily, 4H, and 1H levels when they improve the current map: `MONTHLY SUPPLY`, `MONTHLY DEMAND`, `WEEKLY SUPPLY`, `WEEKLY DEMAND`, `DAILY SUPPLY`, `DAILY DEMAND`, `4H DEMAND`, `4H SUPPLY`, `1H SUPPLY`, and `1H DEMAND`.
- `Monthly` and `Weekly` remain macro context-only.
- `Daily` remains operational context inside the preserved HTF layer.
- `4H` remains the structural HTF layer.
- `1H` is an important tactical correlation layer between `4H` and `30m`; it confirms or warns, but it does not execute.
- Higher-timeframe manual levels such as `MONTHLY SUPPLY`, `MONTHLY DEMAND`, `WEEKLY SUPPLY`, `WEEKLY DEMAND`, `DAILY SUPPLY`, `DAILY DEMAND`, `4H DEMAND`, `4H SUPPLY`, `1H SUPPLY`, and `1H DEMAND` must be drawn as infinite horizontal lines.
- 5m execution lines remain execution-only, but the fixed chart directive is now endless horizontal lines from left to right.
- Macro context, `Daily`, and `1H` must never replace `4H` or `5m` in the decision hierarchy.

## Entry Markup Standard

- Default entry markup is `ENTRY + TP1 + TP2 + TP3 + SL` using short, finite, bounded horizontal lines only.
- Do not draw risk/reward rectangles by default.
- Every execution line must stay visually short and compact near the active setup area.
- Every execution line must carry its own text inside the line, centered.
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

- A macro / Daily / 4H / 1H idea may remain valid while the old 5m execution line is no longer tradable.
- Before preserving a 5m execution line, classify it as `ACTIVE`, `STALE`, or `INVALIDATED`.

Definitions:

- `ACTIVE`: still near current price and still structurally usable.
- `STALE`: still informative, but too far from current price, already chased,
  structurally behind the current tape, or no longer the cleanest trigger.
- `INVALIDATED`: clearly broken, accepted through, mitigated too many times, or replaced by a cleaner trigger.

Rules:

- Remove `INVALIDATED` 5m execution lines from the chart.
- Remove or demote `STALE` 5m execution lines unless they still matter as invalidation or context.
- Do not let `STALE` 5m lines dominate the decision.
- Never keep an old 5m execution line as the active trade idea if the chart has materially moved on and a new cleaner trigger exists closer to price.
- Prefer one primary active `5M EXECUTION LONG` and one primary active `5M EXECUTION SHORT` per symbol unless an older level still matters as invalidation or structural reference.
- When a new active 5m pair is promoted, remove the obsolete old 5m pair instead of letting both pairs coexist.
- That hard cleanup applies to the 5m execution map only, not to preserved higher-timeframe manual levels.

## Mandatory Far-From-Price Refresh Trigger

Even without a hard invalidation, a `5m` pair becomes a mandatory reassess
candidate when both execution levels are structurally far from current price
and no longer help classify `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED`.

Use structural relation, not a fixed point threshold:

- price already moved well past the intended execution bracket
- the pair now sits behind the current market structure
- the pair no longer defines the nearest clean long/short decision shelves
- keeping the pair active would force a late read or stale map

When that happens:

- mark the old pair `STALE` or `INVALIDATED` as appropriate
- perform a full reassess + redraw
- preserve HTF if unchanged
- replace only the execution layer that truly moved on

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
- Use `1H` as tactical correlation, `30m` as the session structure bridge, `15m` as the minimum setup-quality filter, and `5m` as execution only; do not let isolated `5m` noise promote a setup without the intended `1H/30m/15m` support.
- Use simple structure language when possible: `HH/HL`, `LH/LL`, swing high, swing low, break, reclaim, rejection.

## Chart Actions Standard

When preserving or updating levels:

- Update the desired chart state first. Do not depend on direct chart clicks from inside the automation run.
- Treat every reassessment as a declarative redraw of the automation-owned layer, not as a partial cosmetic tweak.
- Preserve relevant `Monthly`, `Weekly`, and `Daily` levels unless the higher-timeframe thesis clearly changed.
- Preserve relevant 4H levels unless structure clearly invalidates them.
- Preserve relevant 1H levels when they clarify tactical acceptance, rejection, or transition; omit them when they add noise.
- Treat preserved macro, `Daily`, `4H`, and `1H` levels as infinite HTF / tactical structure, not as short execution segments.
- Rebuild kept lines so their embedded text stays centered in-line.
- Remove duplicate labels and duplicate lines.
- Force the explicit color palette above.
- Automation-owned shapes must remain editable and savable; do not introduce flags that lock them or disable saving/selection.
- Re-evaluate `Monthly / Weekly / Daily / 4H / 1H` every live cycle, but redraw preserved HTF only when
  higher-timeframe structure materially changed.
- Remove invalidated 5m execution lines.
- Remove or demote stale 5m execution lines if they no longer help execution.
- Add a new 5m execution line only when a cleaner and more current trigger truly exists.
- If the task is only to refresh 5m entries, do not wipe the HTF layer while cleaning the old 5m pair.
- If the task is only to refresh `5m` entries, preserve macro, `Daily`, `4H`, and useful `1H` levels unless there is a real HTF reason to refresh them.
- When the user confirms an entry, mark the trade with short bounded lines for `ENTRY`, `TP1`, `TP2`, `TP3`, and `SL` rather than boxes.

## Chart Note Standard

`CHART NOTE` is the only approved planning-only exception to the drawing
vocabulary.

Rules:

- use it only before risk permission exists
- keep it lightweight, clearly non-executable, and visually distinct from
  `ENTRY`
- do not let it masquerade as active trade markup
- remove it when:
  - real trade permission exists and entry markup is drawn
  - the setup expires
  - the workflow refreshes away from that idea
- `ENTRY / SL / TP1 / TP2 / TP3` still require valid risk permission

## Articuno Chart-Marking Reinforcement

- Articuno does not change the drawing vocabulary of the engine.
- Articuno only improves:
  - level selection
  - level lifecycle classification
  - whether a level is `ACTIVE`, `STALE`, or `INVALIDATED`
  - whether trade markup is permitted by risk
  - whether `desired_state` should be preserved, refreshed, simplified, or left untouched
- Before updating `desired_state`, use Articuno only to ask whether the current `DAILY SUPPLY`, `DAILY DEMAND`, `4H DEMAND`, `4H SUPPLY`, `5M EXECUTION LONG`, or `5M EXECUTION SHORT` still have real structural and liquidity quality.
- Articuno may reinforce whether `ENTRY / SL / TP1 / TP2 / TP3` markup is allowed, but only through the existing risk model.
- Do not mark random micro pivots as execution levels.
- Do not draw fresh entry levels after liquidity has already been paid.
- Do not repackage a late setup as a fresh desired-state update.
- Do not add new shapes, boxes, OB zones, FVG zones, trendline systems, or indicator drawings.
- Keep HTF infinite.
- Keep 5m execution-only while rendering it as endless horizontal lines.
- Keep semantic colors unchanged.
- Keep `desired_state` authoritative.

## Reassessment Redraw Standard

When a workflow or manual trigger performs a full reassessment:

- Re-read continuity memory, marking rules, and desired state before deciding whether the old 5m pair is still `ACTIVE`, has become `STALE`, or is `INVALIDATED`.
- Re-read the market runtime status files to determine whether the workflow is
  in normal mode, `recovery pending`, or `recovery ready`.
- If the workflow is stalled and the required symbol set is valid again,
  execute a full recovery reassess + redraw.
- If the active 5m pair changed, fully clear the automation-owned drawing layer and rebuild it from desired state instead of stacking generations.
- The rebuilt owned layer should contain only:
  - the preserved HTF pair
  - the current active 5m pair
  - optional `CHART NOTE` when planning context is still allowed
  - optional current trade-entry markup if there is an active user-confirmed trade
- After rebuild, there should be exactly one clean line with one embedded centered text payload per owned level.
- If visual verification shows duplicate execution lines, duplicate labels, or interposed text, the reassessment is not complete and the runtime must rebuild again.
- Never let `ON HIGH`, `ON LOW`, `PDH`, `PDL`, old trade-entry marks, or earlier 5m generations survive a reassessment unless they are explicitly present in desired state for that symbol.

## Shared Memory Update Standard

When updating `SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md`, explicitly record:

- which 5m execution lines remained `ACTIVE`
- which became `STALE`
- which were `INVALIDATED`
- what the opportunity timing state was: `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED`
- what the redraw status was:
  - `preserved`
  - `refreshed`
  - `recovery-driven`
- what the `refresh_reason` was:
  - `stall_recovery`
  - `5m_far_from_price`
  - `htf_changed`
  - `manual_reassessment`
- whether the read used a transcript-derived refinement rule or coaching note from the compatibility matrix / timing addendum
- which line texts were re-centered or rebuilt
- which levels were recolored, removed, or replaced

## Failure Handling

- If a newly created or preserved markup does not visually match these rules, do not keep it just because it exists.
- Fix it immediately, or remove it and rebuild it cleanly.
- Direct TradingView MCP tool calls are forbidden in the automation analysis path.
- If a required market live-state file is stale or `DATA_DEGRADED`, do not bypass it with a direct live read from inside the automation. Wait briefly for the local market runtime to refresh it, then preserve the prior map for that symbol if it still fails.
- If the market runtime reports `workflow_stalled` or `recovery_pending`, do
  not publish a fake fresh redraw. Wait for the required symbol set or preserve
  the old map while explicitly marking recovery as pending.
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
- Also read:
  - `market_runtime/market_runtime_state.json`
  - `market_runtime/market_watchdog_state.json`
- In normal operation, if one symbol is `FULL_DATA` and the other is
  `DATA_DEGRADED`, analyze the fresh symbol and preserve the degraded symbol.
- In normal operation, if both symbols are `DATA_DEGRADED`, preserve prior maps
  and do not invent new setup decisions.
- During stalled recovery, use the workflow-required symbol set:
  - New York workflows wait for both symbols before a recovery redraw
  - Asia workflows wait for `XAUUSD` only
