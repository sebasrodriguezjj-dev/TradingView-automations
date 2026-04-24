# Entry & Timing Addendum

Use this addendum to refine entries and timing without changing the core strategy.

This file is subordinate to the main strategy hierarchy:

- `Daily / 4H` define context
- `30m` organizes session structure
- `15m` validates setup quality
- `5m` executes

## Purpose

Refine:

- what counts as a real trigger
- when a setup is alive
- when a setup is already late
- when the correct action is to wait, execute, manage, or stand down

## Definitions

### Indication

An `indication` is the first meaningful sign that the prior local structure may be failing or reversing.

Examples:

- break of a meaningful swing high or swing low
- initial rejection from a defined level
- first push away from a defended liquidity shelf

Rules:

- an indication is not enough by itself to force the trade
- it is an alert, not automatic execution

### Correction

A `correction` is the move after the indication that tests whether the market is really changing behavior or just faking out.

What it is used for:

- filtering fakeouts
- checking whether the market accepts the new direction
- deciding whether lower timeframe structure confirms the idea

Rules:

- a correction should not be treated as failure by default
- the correction is often where the better entry is built
- do not chase the first impulse if the cleaner correction / retest has not formed yet

### Continuation

A `continuation` is the move that resumes in the intended direction after the correction confirms the idea.

Rules:

- continuation is preferred when it follows clean structure and level interaction
- continuation is weaker if it is already overextended or far from the intended trigger shelf

## Entry Timing Model

Every setup must be classified as one of these:

- `PRE-TRIGGER`
- `ARMED`
- `TRIGGERED`
- `EXPIRED`

### PRE-TRIGGER

The idea exists, but price has not reached the meaningful shelf or the setup still lacks rejection / reclaim.

Correct action:

- wait
- state what exact level or condition is still missing

### ARMED

Price is at or near the trigger zone and one more confirmation can activate the trade.

Minimum evidence:

- level interaction is live now
- `15m` does not conflict in a way that invalidates the idea
- `5m` is showing the beginning of confirmation

Correct action:

- watch the exact trigger
- state the exact price or condition that flips the setup to `TRIGGERED`

### TRIGGERED

The retest, rejection, reclaim, or break already happened and the move has already started.

Correct action must be one of:

- `manage if already in`
- `do not chase`
- `wait for new retest`

Rules:

- do not keep calling the setup `WAIT for retest`
- do not keep calling it fresh if the intended entry already passed

### EXPIRED

The idea is no longer high quality because:

- price already moved too far
- the structure failed
- the trigger was used and is no longer the cleanest location

Correct action:

- do not force the trade
- wait for a new map or a new retest

## Minimum Evidence For Entry Quality

### 15m

Use `15m` to decide whether the setup is mature enough.

Look for:

- clear support / resistance interaction
- reclaim or rejection that matches the intended direction
- structure that supports, not contradicts, the `30m` read

Do not promote the setup if `15m` is still clearly unresolved.

### 5m

Use `5m` only to execute.

Look for:

- live interaction with the active shelf
- rejection, reclaim, failed retest, or structure shift
- a clear relation to nearest buy-side or sell-side liquidity

Do not use `5m` noise alone to overturn the higher-timeframe thesis.

## No-Chase Rule

Do not chase when:

- the retest already happened and price already left the entry area
- the move already reached the first intended objective
- the setup is only attractive because the candle is moving fast

If the idea is still valid but the entry already passed:

- mark it as `TRIGGERED / DO NOT CHASE`
- or `EXPIRED / WAIT FOR NEW RETEST`

## Markup Guidance

When promoting or refreshing a `5m` pair:

- prefer the nearest meaningful shelf, not random pivots
- tie it to liquidity, a sweep, or a post-sweep reaction
- keep the map tight and relevant to current price
- let stale `5m` levels die when a cleaner trigger exists

## Coaching Layer

For live alerts and reassessments, include a short explanation:

- what price did
- why it matters
- what is still missing or what already happened
- what to do now

Keep this short and trader-facing.
