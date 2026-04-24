# TradingView Automation Engine

## Implementation Mode

Platform limitation found during setup:

- Codex allows only **one heartbeat automation attached to a thread**.
- Because you asked for a connected automation engine with scheduled workflows plus an on-demand reassessment trigger, the clean practical workaround is:
  - create the 8 scheduled workflows as **cron automations**
  - add one paused manual trigger automation for live reassessment when you want to press play
  - make all 9 read and update the same shared continuity file:
    - [SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md)

That shared file is now the engineâ€™s cross-automation memory layer.

## Chart Marking Rules

The workflow now has a dedicated chart-marking rules file:

- [WORKFLOW_MARKING_RULES.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/WORKFLOW_MARKING_RULES.md)

Every automation must read that rules file together with:

- [SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md)
- [TRANSCRIPT_COMPATIBILITY_MATRIX.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/TRANSCRIPT_COMPATIBILITY_MATRIX.md)
- [ENTRY_TIMING_ADDENDUM.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/ENTRY_TIMING_ADDENDUM.md)
- [COMMUNICATION_STYLE_GUIDE.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/COMMUNICATION_STYLE_GUIDE.md)

Those rules are now mandatory for:

- label repositioning back to the right side on every workflow run
- explicit semantic colors instead of gray or default-neutral lines
- 5m execution-line lifecycle management (`ACTIVE`, `STALE`, `INVALIDATED`)
- opportunity timing-state management (`PRE-TRIGGER`, `ARMED`, `TRIGGERED`, `EXPIRED`)
- decision freshness so the action state reflects both higher-timeframe thesis and current execution readiness
- line-only execution markup for confirmed entries: `ENTRY`, `TP1`, `TP2`, `TP3`, and `SL` as short bounded lines instead of boxes
- entry proposals must fit the user's risk model: preferred stop `60-80`, hard max `100`, with `TP1 60`, `TP2 80`, and `TP3 100`
- if a stale 5m execution pair is replaced, remove the obsolete old 5m pair but preserve the HTF manual layer unless higher-timeframe structure itself has changed
- HTF manual structure should usually keep a pair per symbol: `4H SUPPORT` plus `4H RESISTANCE`, both as infinite horizontal lines
- `5M EXECUTION LONG` lines must render in blue and `5M EXECUTION SHORT` lines must render in yellow across the whole automation stack
- transcript-derived refinements may strengthen timing, confirmation, and explanation, but they must never replace the existing strategy hierarchy or risk model

If the rules file and older workflow wording ever conflict, the rules file wins for chart markings, 5m execution-line handling, and final action-state freshness.

## Chart Runtime Layer

Chart drawing is now split from chart analysis.

- The 8 Codex automations still analyze the market and preserve the same strategy logic.
- Automation-owned chart markings are now declared in the desired state files:
  - [chart_runtime/desired_states/PEPPERSTONE_XAUUSD.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/desired_states/PEPPERSTONE_XAUUSD.json)
  - [chart_runtime/desired_states/FOREXCOM_US30.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_runtime/desired_states/FOREXCOM_US30.json)
- The local chart writer is now:
  - [chart_executor.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_executor.py)
- The local watchdog is now:
  - [chart_watchdog.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/chart_watchdog.py)
- Launcher:
  - [start_chart_watchdog.ps1](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_chart_watchdog.ps1)
- Runtime contract:
  - [CHART_AUTOMATION_RUNTIME.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/CHART_AUTOMATION_RUNTIME.md)

Important interpretation rule:

- whenever a workflow prompt says `draw`, `preserve`, `add`, `remove`, or `simplify` chart levels, treat that as updating the desired state JSON, not as issuing direct TradingView drawing commands from inside the automation
- the desired state files are authoritative for automation-owned markings
- the live chart is a rendered view and a verification surface, not the durable source of truth

## Market Runtime Layer

Live market reading is now split from automation analysis.

- The Codex automations still analyze the market and preserve the same strategy logic.
- Live market context is now declared in the snapshot files:
  - [market_runtime/snapshots/PEPPERSTONE_XAUUSD.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/snapshots/PEPPERSTONE_XAUUSD.json)
  - [market_runtime/snapshots/FOREXCOM_US30.json](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_runtime/snapshots/FOREXCOM_US30.json)
- The local live-reader is now:
  - [market_snapshotter.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_snapshotter.py)
- The local watchdog is now:
  - [market_watchdog.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/market_watchdog.py)
- Launcher:
  - [start_market_watchdog.ps1](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_market_watchdog.ps1)
- Runtime contract:
  - [MARKET_AUTOMATION_RUNTIME.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/MARKET_AUTOMATION_RUNTIME.md)

Important interpretation rule:

- automation analysis must read market snapshots and screenshots first, not TradingView MCP tools directly
- TradingView MCP tools are forbidden inside the automation analysis path
- if the required snapshot is older than `30s`, the workflow should wait briefly for refresh and then finish in `STALE SNAPSHOT / DEGRADED` instead of asking for manual approval
- if the structured JSON snapshot is fresh and contains valid market data, continue the trading assessment even if screenshots are missing or older than ideal
- screenshot problems should reduce confidence, not replace the market thesis with a system-health report

## Discord Layer

## Communication Layer

The workflow now has a dedicated communication rules file:

- [COMMUNICATION_STYLE_GUIDE.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/COMMUNICATION_STYLE_GUIDE.md)

This layer governs communication only.

- It does **not** change strategy.
- It does **not** change the engine.
- It does **not** change timing states, levels, risk rules, or chart ownership.
- It changes only how assessments, reports, and Discord notifications are expressed.

Mandatory communication contract for all 9 automations:

- market first
- system second
- `Historia -> Tesis -> Niveles -> Accion`
- trader-facing voice
- same thesis and same decision in reports and Discord
- Discord shorter and more energetic, but not more reckless
- when the setup is `TRIGGERED`, communication becomes more direct
- when the setup is `EXPIRED`, communication must say the opportunity already passed instead of pretending it is still fresh

The workflow logic was preserved.

The 8 scheduled automations keep their original trading logic and now include an appended Discord notification step layered on top. The manual live-reassessment trigger uses the same continuity and desired-state architecture.

Notification objective:

- the Discord layer exists to surface trading context, not to narrate runtime internals
- market thesis, levels, setup state, and action always come first
- runtime health should appear only as a secondary note when it changes the trust level of the market read
- do not emit a system-centric Discord summary when the structured market snapshot is still fresh enough to support trading analysis
- when a transcript-derived coaching heuristic is useful, keep it short and trader-facing: what price did, why it matters, what is still missing or what already happened, and what to do now
- every Discord message must still preserve the exact trading decision even when the tone becomes more live, more human, or more energetic

Current Discord delivery architecture:

- each automation writes its Discord summary to the shared dispatch file:
  - [dispatch.txt](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_payloads/dispatch.txt)
- the automations no longer send Discord directly from inside Codex
- a local watcher runs outside the automation sandbox and detects updates to `dispatch.txt`
- that watcher is:
  - [discord_dispatch_watcher.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_dispatch_watcher.py)
- it is launched through:
  - [start_discord_dispatch_watcher.ps1](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/start_discord_dispatch_watcher.ps1)
- the watcher uses:
  - [discord_notifier.py](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/discord_notifier.py)

This was done so all 8 flows use the same exact send path without depending on direct network access from inside each automation.

Exact Discord config, helper behavior, payload paths, command pattern, and current message shape are documented here:

- [DISCORD_NOTIFICATION_LAYER.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/DISCORD_NOTIFICATION_LAYER.md)

## Scheduling Basis

You asked for **New York time**.

This Codex environment is currently running in `America/Costa_Rica`, so the cron schedules were created at the **current April 2026 Costa Rica equivalents** of the requested New York times:

- `07:30 AM New York` -> `05:30 AM Costa Rica`
- `08:45 AM New York` -> `06:45 AM Costa Rica`
- `09:00 AM New York` -> `07:00 AM Costa Rica`
- `09:20 AM New York` -> `07:20 AM Costa Rica`
- `10:15 AM New York` -> `08:15 AM Costa Rica`
- `12:30 PM New York` -> `10:30 AM Costa Rica`
- `06:30 PM New York` -> `04:30 PM Costa Rica`
- `07:30 PM New York` -> `05:30 PM Costa Rica`

If New York changes between EDT and EST and Codex still lacks per-automation timezone scheduling, these will need a one-hour seasonal adjustment.

## Timeframe Integration Standard

The workflow now uses a four-layer timeframe hierarchy instead of jumping directly from `Daily / 4H` to `5m`.

- `Daily` and `4H` define the directional framework and major supply / demand map.
- `30m` is the structure bridge:
  - confirm whether the higher-timeframe idea is organizing into trend, compression, sweep, or rotation
  - validate whether key 4H levels are being accepted or rejected cleanly
  - identify the cleaner session range or role-flip zone
- `15m` is the setup-quality filter:
  - confirm whether a long or short is building with real structure instead of only 5m noise
  - validate reclaim / rejection / failed-retest behavior before promoting a setup to active
  - keep 5m entries from being forced directly into unresolved 30m structure
- `5m` remains execution-only:
  - exact trigger
  - exact retest
  - invalidation
  - timing
  - nearest buy-side and sell-side liquidity
  - whether the trigger is forming before a sweep, on a sweep, or after a sweep / rejection

Engine rule:

- do not invalidate a `Daily / 4H` thesis from `5m` noise alone
- do use `30m` to decide whether the higher-timeframe thesis is getting cleaner or dirtier
- do use `15m` to decide whether a setup is mature enough to trade
- do use `indication -> correction -> continuation` as a timing refinement inside the existing framework
- do prefer confirmation after correction over chasing the first expansion candle
- only promote `VALID LONG SETUP` or `VALID SHORT SETUP` when `30m`, `15m`, and `5m` are aligned, or when any mismatch is explicitly explained
- do not mark a new 5m entry without stating the nearest liquidity above, the nearest liquidity below, and whether the setup is targeting, sweeping, or rejecting one of those pools
- do classify each live idea as `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED` so the workflow does not keep saying `WAIT` after the best retest already happened
- if the setup is already `TRIGGERED`, the workflow must explicitly say whether the correct action is `manage if already in`, `do not chase`, or `wait for new retest`
- do use simple structure language when possible: `HH/HL`, `LH/LL`, swing high, swing low, break, reclaim, rejection, failed retest

## Transcript Refinement Layer

The transcripts are a refinement source, not a replacement strategy.

- The source of truth remains the existing strategy and risk model documented in this engine, the shared continuity memory, and the chart-marking rules.
- Transcript ideas may be promoted into engine behavior only when they reinforce the existing framework instead of changing it.
- Use [TRANSCRIPT_COMPATIBILITY_MATRIX.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/TRANSCRIPT_COMPATIBILITY_MATRIX.md) to decide whether a transcript concept becomes:
  - a hard rule
  - a coaching note
  - ignored material
- Use [ENTRY_TIMING_ADDENDUM.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/ENTRY_TIMING_ADDENDUM.md) when classifying:
  - `indication`
  - `correction`
  - `continuation`
  - `PRE-TRIGGER`
  - `ARMED`
  - `TRIGGERED`
  - `EXPIRED`
- Promote only concepts that improve timing, confirmation, structure reading, or chart clarity without altering:
  - `Daily / 4H -> 30m -> 15m -> 5m`
  - the user's risk model
  - the line-only execution style
  - the anti-chase posture
- Keep transcript-derived coaching concise. The purpose is to make the trader sharper, not to turn live outputs into course summaries.

## Exact Automations And Prompts

### 1. NY Open Levels

Schedule:

- `Monday-Friday`
- `05:30 AM Costa Rica`
- target intent: `07:30 AM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD and FOREXCOM:US30. This is the baseline thesis for todayâ€™s New York workflow, so set context carefully and keep it practical. Use Daily and 4H to define direction. Use 30m to map session structure, 15m to validate setup quality, and 5m only for execution timing. Prioritize supply/demand, structure, breakout/retest, rejection, confirmation, and clean level interaction. RSI is secondary and must stay brief. If structure is mixed, explicitly say WAIT / NO CLEAR EDGE.

For each symbol, produce a Spanish report with:
- HIGHER-TIMEFRAME BIAS: Daily directional bias, 4H directional bias, whether they are aligned, strength of bias, and whether to prefer longs, shorts, or patience.
- INTERMEDIATE STRUCTURE: what the 30m says about session structure, what the 15m says about setup quality, and whether those timeframes support or conflict with the Daily / 4H idea.
- LIQUIDITY MAP: nearest buy-side liquidity, nearest sell-side liquidity, whether price is more likely to target one first, and whether a 5m setup should wait for a sweep before execution.
- KEY STRUCTURE: current structure, whether supply or demand is being respected, whether prior support became resistance or resistance became support, and any clear change of character or failure to change character.
- MOST IMPORTANT LEVELS: 2 higher-timeframe 4H support/resistance levels, 2 execution levels on 5m, PDH, PDL, overnight high/low if visible, and the nearest clean buy-side and sell-side liquidity. Choose only the clearest actionable levels.
- RSI CONTEXT: current RSI value and whether it is overbought, oversold, or neutral, briefly.
- EXECUTION READINESS: what must happen for a valid long, what must happen for a valid short, which liquidity event must happen first if any, what invalidates both sides, and what not to do right now. A 5m entry is only valid if it is either targeting a clear liquidity pool or confirming after a sweep / reclaim / rejection.
- 3-LINE CONCLUSION IN SPANISH: what the market is doing now, what is more likely next if structure holds, and what to avoid right now.

Chart actions:
- Update the desired chart state for this workflow instead of drawing directly from the automation. The local chart executor will reconcile the chart.
- Draw 4H higher-timeframe support and resistance lines.
- Treat 4H higher-timeframe support and resistance as persistent infinite lines, not as short execution segments.
- Keep a meaningful `4H SUPPORT` / `4H RESISTANCE` pair on the chart when both sides still matter.
- Draw 5m execution lines only at liquidity-targeting or post-sweep execution zones.
- Keep 5m execution lines short and finite so they stay visually distinct from HTF structure.
- Use uppercase labels: 4H RESISTANCE, 4H SUPPORT, 5M EXECUTION SHORT, 5M EXECUTION LONG, PDH, PDL, ON HIGH, ON LOW.

After finishing the analysis, update the shared continuity file with todayâ€™s New York baseline thesis, the drawn levels for both symbols, the current preferred side, and a fresh log entry for this automation.

End with a short Spanish thread update confirming both symbols were reviewed, the directional bias for each, which levels were drawn on each, and which symbol looks cleaner for the NY open.
```

### 2. Post Open Validation

Schedule:

- `Monday-Friday`
- `06:45 AM Costa Rica`
- target intent: `08:45 AM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Continue from NY Open Levels. Before analyzing, read the current New York baseline, the previously recorded levels, and the latest workflow notes from the shared continuity file. Also inspect the latest desired-state chart map plus the local market-runtime screenshots. Use that prior context as baseline. Do not rebuild from scratch unless price action has clearly invalidated the previous framework. Lower-timeframe noise alone is not enough to invalidate the higher-timeframe thesis.

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD and FOREXCOM:US30 and produce a Spanish report with:
- OPEN VALIDATION: whether the New York open is confirming or rejecting the higher-timeframe bias, whether price is accepting above or below key levels or rejecting them, and whether the open created a breakout, failed breakout, sweep, retest, or consolidation. State whether the move is clean or erratic.
- STRUCTURE AND EXECUTION: the clearest 30m structure, the 15m setup-quality read, the 5m trigger state right now, whether a valid long setup is forming, whether a valid short setup is forming, whether the current 5m move is targeting liquidity or reacting after taking it, what exact confirmation is still missing, and what would invalidate the current idea.
- OPPORTUNITY TIMING: classify the current execution opportunity as `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED`. If it is already `TRIGGERED`, say clearly whether the correct action is `manage if already in`, `do not chase`, or `wait for new retest`.
- LEVEL INTERACTION: which previously drawn levels are being respected, which are failing, whether PDH, PDL, ON HIGH, or ON LOW have been swept or reclaimed, whether the nearest liquidity has already been been taken or remains untouched, and whether price is reacting cleanly at 4H support/resistance or 5m execution levels.
- TRADING DECISION: Prefer LONGS, SHORTS, WAIT, or NO CLEAR EDGE; which symbol is cleaner right now; which symbol should be avoided; and the biggest trap at this moment.
- 3-LINE CONCLUSION IN SPANISH: what the open is doing, what is tradable now if anything, and what to avoid right now.

Chart actions:
- Update the desired chart state for this workflow instead of drawing directly from the automation. The local chart executor will reconcile the chart.
- Preserve the relevant 4H and 5m levels from NY Open Levels.
- Preserve the HTF layer even when refreshing the 5m execution map.
- Keep preserved 4H levels as infinite lines and do not redraw them as short execution-style segments.
- Add a new 5m execution line only if the open created a clearer trigger zone tied to liquidity targeting or post-sweep rejection / reclaim.
- Keep uppercase labels consistent.

After finishing the analysis, update the shared continuity file with whether each symbol validated, rejected, weakened, or partially confirmed the pre-market thesis, plus any new execution levels and a fresh log entry for this automation.

End with a short Spanish thread update confirming whether XAUUSD and US30 validated or rejected the pre-market bias, which symbol is cleaner after the open, and whether the correct action is trade now or wait.
```

### 3. Active Setup Detector

Schedule:

- `Monday-Friday`
- `07:00 AM Costa Rica`
- target intent: `09:00 AM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Continue from NY Open Levels and Post Open Validation. Before analyzing, read the current New York baseline, prior validation result, preserved levels, and latest workflow notes from the shared continuity file. Also inspect the latest desired-state chart map plus the local market-runtime screenshots. Use that prior context as baseline. Do not restart from scratch unless price has clearly invalidated the previous framework.

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD and FOREXCOM:US30 and determine for each symbol whether there is:
- VALID LONG SETUP
- VALID SHORT SETUP
- WAIT
- NO CLEAR EDGE

Also provide:
- which key level is being tested now
- whether price is confirming or failing the prior directional idea
- what exact trigger is present
- what the 30m and 15m are saying about setup quality right now
- which liquidity is nearest above and below, and whether the setup is targeting or reacting after that liquidity event
- what exact confirmation is still missing if not yet active
- whether the setup is `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED`
- what invalidates the setup
- which symbol is currently cleaner
- which symbol should be avoided
- a short execution-focused summary in Spanish

Chart actions:
- Update the desired chart state for this workflow instead of drawing directly from the automation. The local chart executor will reconcile the chart.
- Preserve relevant levels from prior automations.
- Preserve the HTF layer as infinite lines while refreshing the 5m map.
- Add a new 5m execution line only if price action has created a clearer trigger zone.
- Keep uppercase labels consistent.

After finishing the analysis, update the shared continuity file with setup status for both symbols, any new trigger levels, which symbol is cleaner, and a fresh log entry for this automation.

End with a short Spanish thread update confirming whether a valid setup is active, on which symbol, in which direction, or whether the correct action is still to wait.
```

### 4. Bias Integrity Check

Schedule:

- `Monday-Friday`
- `07:20 AM Costa Rica`
- target intent: `09:20 AM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Continue from the earlier New York workflow. Before analyzing, read the morning baseline thesis, the validation result, the setup status, the preserved levels, and the latest workflow notes from the shared continuity file. Also inspect the latest desired-state chart map plus the local market-runtime screenshots. Use that prior context as baseline. Do not overreact to lower-timeframe noise. Only weaken or invalidate the thesis if price action has caused meaningful structural failure relative to the prior context, and use 30m / 15m structure plus liquidity sweep behavior before downgrading a Daily / 4H thesis from 5m behavior alone.

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD and FOREXCOM:US30 and state for each symbol:
- BIAS INTACT
- BIAS WEAKENED
- BIAS INVALIDATED

Then explain:
- which previously important level or structural condition is still holding
- which important level or condition has failed, if any
- which liquidity pool has already been taken or remains untapped
- whether the higher-timeframe thesis is still usable
- whether the same directional idea still deserves focus
- whether the thesis is being damaged by genuine structural failure or just short-term noise
- which symbol still has the cleaner directional case
- what I should stop assuming if the thesis is weakening

Chart actions:
- Update the desired chart state for this workflow instead of drawing directly from the automation. The local chart executor will reconcile the chart.
- Preserve relevant levels.
- Remove only levels that are clearly no longer relevant.
- Keep the HTF manual pair as infinite lines unless higher-timeframe structure itself invalidates one side.
- Add updated 5m execution lines only if necessary and tied to a clear liquidity objective or post-sweep reaction.
- Preserve label consistency.

After finishing the analysis, update the shared continuity file with intact / weakened / invalidated status for each symbol, any removed or added levels, the cleaner symbol, and a fresh log entry for this automation.

End with a short Spanish thread update confirming whether each symbolâ€™s bias is intact, weakened, or invalidated, which symbol still deserves focus, and whether the original plan should be maintained or conviction reduced.
```

### 5. Mid-Session Reassessment

Schedule:

- `Monday-Friday`
- `08:15 AM Costa Rica`
- target intent: `10:15 AM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Continue from the full New York workflow already stored in the shared continuity file. Do not reinvent the day. Reassess the original thesis using everything that has happened so far, plus the latest desired-state chart map and local market-runtime screenshots. Preserve the higher-timeframe hierarchy: Daily and 4H define context, 30m organizes the session structure, 15m filters setup quality, and 5m only refines execution.

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD and FOREXCOM:US30 and assess:
- whether the original morning thesis is still alive
- whether the best opportunity has already passed
- whether the market is now cleaner, dirtier, trending, or rotating
- whether one symbol remains significantly better than the other
- whether I should still wait for a better level
- whether the best remaining move is still toward untouched liquidity or whether the obvious liquidity has already been taken
- whether momentum or patience is now the better approach
- whether the open structure evolved into continuation, reversal, or dead range
- whether the best setup is still `PRE-TRIGGER`, is currently `ARMED`, already `TRIGGERED`, or already `EXPIRED`

Then provide:
- the best remaining opportunity, if any
- the biggest trap still present
- what not to chase now
- a short trader-focused summary in Spanish

Chart actions:
- Update the desired chart state for this workflow instead of drawing directly from the automation. The local chart executor will reconcile the chart.
- Preserve the relevant map.
- Keep the HTF pair (`4H SUPPORT` / `4H RESISTANCE`) as infinite lines if still relevant.
- Simplify clutter if too many short-term levels were added.
- Keep only the levels that still matter, and limit hard cleanup to the 5m execution layer unless the HTF thesis itself changed.
- Preserve label consistency.

After finishing the analysis, update the shared continuity file with whether the morning plan is still alive, whether the opportunity already passed, which symbol remains better, the remaining levels that matter, and a fresh log entry for this automation.

End with a short Spanish thread update confirming whether the plan remains valid, whether the opportunity is still ahead, already passed, or not worth forcing, and which symbol remains best or whether neither has edge now.
```

### 6. End-of-Day Review

Schedule:

- `Monday-Friday`
- `10:30 AM Costa Rica`
- target intent: `12:30 PM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Continue from the full New York workflow already recorded in the shared continuity file. Review the morning baseline, post-open validation, active setup status, bias integrity, and mid-session reassessment before writing the end-of-day review. Use those earlier records plus the chart levels and labels that mattered as the baseline for comparison.

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD and FOREXCOM:US30 and produce a Spanish end-of-day review with:
- SESSION REVIEW: what actually happened in each symbol; whether the original bias held, weakened, or failed; which levels mattered most; which levels failed; whether the day was trend continuation, reversal, range, or mixed structure; which symbol was cleaner; where the best opportunity was; what the biggest trap was; and what should have been avoided.
- STRATEGY LEARNING: what today reinforced about the strategy, what weakness or blind spot it exposed, whether the market rewarded patience, confirmation, aggression, fade, breakout, or range thinking, whether Daily + 4H alignment was useful, whether 5m execution helped or created noise, and the main lesson to carry into tomorrow.
- MULTI-DAY INTELLIGENCE: compare today against any prior daily reviews already preserved in the shared continuity file and update recurring observations such as when XAUUSD trades cleaner than US30, when US30 trades cleaner than XAUUSD, how often pre-market bias survives the open, how often PDH / PDL / ON HIGH / ON LOW sweeps lead to continuation or reversal, which structure types are producing the cleanest moves, and when the preferred setup is working best or worst. If continuity is still limited, structure this section so it becomes cumulative over time.

After finishing the review, update the shared continuity file with todayâ€™s session result, the main lesson for tomorrow, and any new multi-day observations that deserve to persist.

End with a short Spanish thread update summarizing the day in trader language, confirming what worked, what failed, and the main lesson for tomorrow.
```

### 7. Asia Session Gold

Schedule:

- `Monday-Friday`
- `04:30 PM Costa Rica`
- target intent: `06:30 PM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD. This is the baseline thesis for the Asia workflow. Use Daily and 4H to define direction. Use 30m to map session structure, 15m to validate setup quality, and 5m only for execution timing. Prioritize supply/demand, structure, breakout/retest, rejection, confirmation, and clean level interaction. RSI is secondary and must stay brief. If structure is mixed, explicitly say WAIT / NO CLEAR EDGE.

Produce a Spanish pre-session report with:
- Daily directional bias
- 4H directional bias
- whether Daily and 4H are aligned
- what the 30m says about the current Asia session structure
- what the 15m says about whether the setup is clean or noisy
- nearest buy-side liquidity and nearest sell-side liquidity
- bias strength: weak, moderate, or strong
- current structure: trend continuation, breakout, failed breakout, retest, consolidation, or transition
- whether supply or demand is being respected
- whether price is entering Asia in expansion or in range conditions
- 2 higher-timeframe 4H support/resistance levels
- 2 execution levels on 5m
- PDH and PDL
- current range high and range low if clearly visible
- current RSI value as secondary context only
- what must happen for a valid long during Asia
- what must happen for a valid short during Asia
- whether Asia should wait for a liquidity sweep before any 5m trigger
- whether conditions favor breakout, fade, or range trading
- what invalidates both sides
- what not to do right now
- a 3-line conclusion in Spanish

Chart actions:
- Update the desired chart state for this workflow instead of drawing directly from the automation. The local chart executor will reconcile the chart.
- Draw 4H higher-timeframe support and resistance lines.
- Treat those 4H levels as infinite lines and keep a meaningful support/resistance pair when both sides still matter.
- Draw 5m execution lines only at liquidity-targeting or post-sweep execution zones.
- Keep 5m execution lines short and finite so they stay visually distinct from HTF structure.
- Use uppercase labels: 4H RESISTANCE, 4H SUPPORT, 5M EXECUTION SHORT, 5M EXECUTION LONG, PDH, PDL, RANGE HIGH, RANGE LOW.

After finishing the analysis, update the shared continuity file with the Asia baseline thesis for gold, the drawn levels, the preferred side or patience state, and a fresh log entry for this automation.

End with a short Spanish thread update confirming gold was reviewed, the directional bias, which levels were drawn, and whether Asia looks tradable or better for patience.
```

### 8. Asia Setup Detector

Schedule:

- `Monday-Friday`
- `05:30 PM Costa Rica`
- target intent: `07:30 PM New York`

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

Continue from Asia Session Gold. Before analyzing, read the current Asia baseline, the preserved levels, and the latest Asia workflow notes from the shared continuity file. Also inspect the latest desired-state chart map plus the local market-runtime screenshots. Use that prior context as baseline. Do not rebuild from scratch unless price has clearly invalidated the earlier Asia framework. Lower-timeframe noise alone is not enough to invalidate the higher-timeframe thesis.

Review the latest local market snapshots and screenshots for PEPPERSTONE:XAUUSD and determine whether there is:
- VALID LONG SETUP
- VALID SHORT SETUP
- WAIT
- NO CLEAR EDGE

Also provide:
- which key level is being tested now
- whether current price action is confirming or failing the Asia bias
- what exact trigger is present
- what exact confirmation is still missing if not active
- what invalidates the setup
- whether conditions still favor breakout, fade, or range behavior
- a short execution-focused summary in Spanish

Chart actions:
- Update the desired chart state for this workflow instead of drawing directly from the automation. The local chart executor will reconcile the chart.
- Preserve relevant Asia levels.
- Preserve the HTF layer as infinite lines while refreshing the 5m execution map.
- Add a new 5m execution line only if current price action creates a clearer trigger zone tied to liquidity targeting or post-sweep rejection / reclaim.
- Preserve label consistency.

After finishing the analysis, update the shared continuity file with the Asia setup status, any new execution trigger levels, whether conditions favor breakout, fade, or range, and a fresh log entry for this automation.

End with a short Spanish thread update confirming whether a valid Asia setup is active, in which direction, or whether the correct action is still to wait.
```

### 9. Live Reassessment Trigger

Schedule:

- `Paused by default`
- intended use: manual `play` when a full live reassessment and 5m realignment is needed

Prompt:

```text
Use this shared continuity file as mandatory baseline memory: C:\Users\sebas\Documents\Codex\2026-04-18-corre-la-herramienta-tv-health-check\SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md

This is a full live reassessment trigger for PEPPERSTONE:XAUUSD and FOREXCOM:US30. Preserve the existing strategy logic exactly: Daily and 4H define context, 30m organizes structure, 15m validates setup quality, and 5m is execution-only. Do not drift the strategy, the risk model, or the decision hierarchy.

Before deciding anything:
- read the shared continuity file
- read the workflow marking rules
- read the chart runtime contract
- inspect the current desired state files for both symbols
- inspect the live chart state

Then perform a full reassessment for XAUUSD and US30:
- confirm the current higher-timeframe thesis
- confirm whether the old 5m execution pair is still ACTIVE, has become STALE, or is INVALIDATED
- confirm whether the current opportunity is still `PRE-TRIGGER`, is `ARMED`, already `TRIGGERED`, or already `EXPIRED`
- if the old 5m pair is still ACTIVE, keep it
- if the old 5m pair is STALE or INVALIDATED, replace it with the cleanest current pair that matches the strategy and the user's risk model
- do not change HTF levels unless higher-timeframe structure itself changed
- explicitly identify nearest buy-side liquidity, nearest sell-side liquidity, and whether the market is targeting, sweeping, or rejecting those pools
- keep the final action state honest: LONGS, SHORTS, WAIT, or NO CLEAR EDGE

Chart actions:
- update the desired chart state instead of drawing directly
- preserve the HTF layer as infinite lines
- rebuild the 5m execution layer only if the pair changed or the chart hygiene is broken
- if a reassessment rebuild happens, the owned drawing layer must end with one clean line and one right-side label per owned level, with no duplicate generations and no interposed text over active candles
- keep `5M EXECUTION LONG` blue and `5M EXECUTION SHORT` yellow

After finishing:
- update the shared continuity file with which 5m lines stayed ACTIVE, which became STALE, which were INVALIDATED, and what was replaced
- record whether the current opportunity finished the reassessment as `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED`
- update the desired state files if needed
- leave a concise Spanish thread update confirming the current thesis, the active 5m pair for each symbol, and whether the map was refreshed or preserved
```

## Continuity Model

- All 9 automations point to the same workspace and the same shared continuity file:
  - [SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md](C:/Users/sebas/Documents/Codex/2026-04-18-corre-la-herramienta-tv-health-check/SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md)
- `NY Open Levels` creates the baseline thesis for the New York chain.
- `Post Open Validation`, `Active Setup Detector`, `Bias Integrity Check`, and `Mid-Session Reassessment` explicitly read that baseline before deciding anything.
- `End-of-Day Review` reads the full day sequence and writes multi-day observations back into the same continuity file.
- `Asia Session Gold` creates the Asia baseline for XAUUSD.
- `Asia Setup Detector` reads that Asia baseline before deciding setup status.
- `Live Reassessment Trigger` can be played manually at any time to perform a full current-market reassessment and 5m realignment without changing the base strategy.
- The current chart labels and levels are treated as live context, and the shared file is treated as durable context.

## Main Risks / Limitations

- The largest platform limitation is scheduling timezone support. These automations were scheduled to match New York time using the **current April 2026 Costa Rica equivalents**, so New York DST changes may require a manual one-hour adjustment later.
- Chart continuity is only as good as the TradingView layout continuity. If symbols, layouts, or manually drawn levels are cleared between runs, the engine still preserves analytical continuity through the shared file, but some visual context may need to be recreated.
- Because the engine is implemented as cron automations rather than heartbeats, continuity is preserved through the shared state file instead of a single persistent thread. This is the cleanest practical workaround available with the current platform limitation.

