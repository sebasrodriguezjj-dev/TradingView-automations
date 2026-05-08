# Watcher Recovery Reassessment

## Purpose

This file defines the official blind recovery reassessment used by the local
watcher bridge after a TradingView / CDP / snapshot stall.

It is not a new strategy.
It is not a new automation schedule.
It is not a standalone signal generator.

It exists only to let the watcher close recovery with the same SMART MONEY /
GOOD MONEY trading logic already approved in the stack.

## Hard Rule

Preserve the existing strategy exactly:

`Monthly / Weekly -> Daily / 4H -> 1H -> 30m -> 15m -> 5m`

Do not change:
- trading strategy
- risk model
- timing states
- action states
- desired-state ownership
- chart drawing vocabulary
- chart executor behavior
- communication identity

Use TradingView Structured Live State as the only live market source.
TradingView MCP tools are forbidden inside this reassessment.
Do not use screenshots for trading decisions.

## Mandatory Inputs

Read these before finalizing:
- `SMART_MONEY_GOOD_MONEY_ENGINE_STATE.md`
- `TRADINGVIEW_AUTOMATION_ENGINE.md`
- `WORKFLOW_MARKING_RULES.md`
- `COMMUNICATION_STYLE_GUIDE.md`
- `ARTICUNO_REINFORCEMENT_LAYER.md`
- `ENTRY_TIMING_ADDENDUM.md`
- `CHART_AUTOMATION_RUNTIME.md`
- `MARKET_AUTOMATION_RUNTIME.md`
- `chart_runtime/desired_states/PEPPERSTONE_XAUUSD.json`
- `chart_runtime/desired_states/FOREXCOM_US30.json`
- `market_runtime/live_state/PEPPERSTONE_XAUUSD.json`
- `market_runtime/live_state/FOREXCOM_US30.json`
- `market_runtime/market_runtime_state.json`
- `market_runtime/market_watchdog_state.json`

## Recovery Reassessment Contract

This run is only valid when:
- `XAUUSD` and `US30` both have structured live data with `decision_allowed = true`
- the reassessment uses the existing liquidity-first logic
- the result updates desired state declaratively instead of drawing directly

Required behavior:
- perform a full reassessment for `PEPPERSTONE:XAUUSD` and `FOREXCOM:US30`
- preserve `Monthly / Weekly -> Daily / 4H -> 1H -> 30m -> 15m -> 5m`
- classify each live opportunity as `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, or `EXPIRED`
- keep anti-chase discipline explicit
- use Articuno only as reinforcement
- preserve HTF if HTF structure did not materially change
- refresh only the execution layer when that is the correct outcome

## Desired-State Acknowledgement Rule

This reassessment is part of a stall recovery.

If the conclusion is that the current map still stands:
- keep the same semantic levels
- keep the same strategy logic
- still rewrite both desired-state files with:
  - fresh `updated_at`
  - bumped `state_version`
  - `refresh_reason = stall_recovery`

Reason:
- the runtime must acknowledge the recovery
- the chart runtime must have permission to redraw a clean authoritative map
- the stall must not remain pending just because the best outcome was preservation

If the conclusion is that one or both maps changed:
- update only the correct owned levels
- keep the drawing vocabulary unchanged
- do not add new shapes or chart systems

## Chart Action Rule

Allowed chart outcomes:
- preserve desired state and force clean redraw
- refresh desired state and force clean redraw
- simplify desired state if a stale layer should be removed
- leave no duplicate generations behind

Forbidden:
- direct TradingView draw/remove actions as the primary delivery path
- boxes
- order-block rectangles
- FVG rectangles
- trendlines
- indicator drawings
- fresh entry markup if risk permission is invalid

## Final Output

Update:
- desired-state JSON files when required by the rules above
- shared continuity memory with a concise recovery reassessment entry

Do not enqueue Discord directly from this reassessment.
The watcher bridge owns post-recovery notification.

Finish with a trader-facing message in this order:

- `Historia`
- `Tesis`
- `Niveles`
- `Accion`

Keep it market-first, concise, and practical.
