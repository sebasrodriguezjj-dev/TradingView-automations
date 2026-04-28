# Articuno Reinforcement Layer

## Purpose

This file is a technical reinforcement layer only.

It reinforces:

- liquidity precision
- level quality
- participation confirmation
- trigger quality
- New York opening context
- trade permission
- anti-chase discipline
- desired-state level-selection quality

The SMART MONEY / GOOD MONEY strategy still produces the thesis.
Articuno only strengthens, weakens, or clarifies the quality of that thesis.

## Hard Rule

The SMART MONEY / GOOD MONEY strategy remains unchanged.

The strategy remains:

- `Daily / 4H -> 30m -> 15m -> 5m`

This layer does **not** create signals.
This layer does **not** modify risk.
This layer does **not** modify timing states.
This layer does **not** modify chart ownership.
This layer does **not** add new drawing types.
This layer does **not** change `chart_executor` behavior.

Articuno may only:

- clarify an existing read
- strengthen or weaken confidence in an existing setup
- improve liquidity precision
- improve level selection
- improve trigger quality
- improve timing-state classification
- improve risk permission
- improve anti-chase discipline
- improve communication clarity
- improve which levels Codex sends to `desired_state`

Articuno must never:

- create standalone trades
- override `Daily / 4H -> 30m -> 15m -> 5m`
- override the risk model
- override timing states
- override desired-state chart ownership
- introduce new setups
- add new drawing types
- turn the engine into an indicator, ORB, OB/FVG, trendline, or standalone VPA strategy

## Seven Reinforcement Lenses

### 1. SMC = Liquidity Precision

What it reinforces:

- nearest buy-side liquidity
- nearest sell-side liquidity
- whether price is targeting, sweeping, rejecting, reclaiming, or has already paid liquidity

Allowed use:

- clarify the real liquidity objective around a current thesis
- improve timing-state classification when liquidity has already been paid
- prevent late entries after the objective already hit

Forbidden use:

- do not enter just because a sweep happened
- do not promote an OB/FVG as a standalone entry
- do not let 5m SMC behavior override HTF context

Checklist:

- Where is nearest buy-side liquidity?
- Where is nearest sell-side liquidity?
- Is price targeting, sweeping, rejecting, or reclaiming?
- Was liquidity already paid?
- Is the current entry fresh or late?
- Does the 5m level exist because of real liquidity or just a random pivot?

Assessment quality effect:

- strengthens timing honesty and anti-chase discipline
- weakens confidence when the move already paid its liquidity objective

Desired-state effect:

- yes, it may improve which 5m execution levels are worth preserving, replacing, or leaving untouched

Rule:

- no 5m execution read is valid unless liquidity above and below are clearly stated

### 2. Supply/Demand = Level Quality

What it reinforces:

- structural quality of `4H SUPPORT`, `4H RESISTANCE`, `5M EXECUTION LONG`, and `5M EXECUTION SHORT`

Allowed use:

- distinguish fresh, tested, mitigated, flip, and displacement-origin levels
- decide whether a level should be preserved, refreshed, marked `STALE`, or marked `INVALIDATED`

Forbidden use:

- do not promote random micro highs/lows into important levels
- do not replace HTF structure with tiny 5m noise
- do not add boxes or rectangles
- do not create standalone supply/demand trades

Checklist:

- Does the level have structural function?
- Is it tied to liquidity?
- Did it create displacement?
- Is it fresh, tested, mitigated, or exhausted?
- Is it HTF relevant or lower-timeframe noise?
- Should this level survive in `desired_state`?

Assessment quality effect:

- improves chart selectivity and reduces clutter
- weakens confidence in levels that are tested, mitigated, or structurally empty

Desired-state effect:

- yes, it directly improves level selection and lifecycle decisions

Rule:

- do not preserve or promote a level unless it has structural function

### 3. VPA = Participation Confirmation

What it reinforces:

- whether a sweep, rejection, breakout, or reclaim had real participation

Allowed use:

- confirm or question the quality of a reaction
- judge effort versus result at key levels
- identify absorption or failed continuation after a sweep

Forbidden use:

- do not create trades from volume alone
- do not use VPA as a standalone system
- do not override structure, liquidity, or risk

Checklist:

- Did high effort produce continuation or fail?
- Did the breakout have participation?
- Did the sweep fail despite strong effort?
- Is there absorption around a key level?
- Does participation confirm or contradict the reaction?

Assessment quality effect:

- raises or lowers confidence in an existing read
- helps separate clean rejection from weak noisy reaction

Desired-state effect:

- sometimes, but only by strengthening or weakening an already valid level or trigger

Rule:

- VPA can confirm or question quality, but it must never create a trade by itself

### 4. Price Action = Trigger Quality

What it reinforces:

- quality of the 5m execution trigger
- cleanliness of the retest, reclaim, rejection, failed retest, and post-correction continuation

Allowed use:

- judge whether the 5m trigger is clean
- evaluate higher low / lower high quality
- improve `PRE-TRIGGER`, `ARMED`, `TRIGGERED`, and `EXPIRED` classification

Forbidden use:

- do not take pure scalps outside the HTF thesis
- do not let 5m override Daily / 4H
- do not enter off the first impulse candle without reaction / confirmation
- do not mark new execution levels from random microstructure

Checklist:

- Is the retest clean?
- Did the reclaim hold?
- Did the rejection confirm?
- Is 5m clean or noisy?
- Is price in correction or extension?
- Has the trigger already fired?
- Is the setup still valid or expired?

Assessment quality effect:

- improves trigger timing and anti-chase accuracy
- helps the engine separate good ideas from late entries

Desired-state effect:

- yes, it may justify refreshing a 5m pair or keeping the old one

Rule:

- 5m confirms execution only; it does not override HTF context

### 5. Opening Range = NY Context

What it reinforces:

- the quality of the New York session read after the first opening impulse

Allowed use:

- contextualize the first NY move
- classify breakout, failed breakout, fakeout, sweep, or post-open retest need
- detect chase risk after the first liquidity target already paid

Forbidden use:

- do not turn this into an automatic ORB strategy
- do not buy every opening-range breakout
- do not sell every opening-range breakdown
- do not add new ORB drawing types

Checklist:

- What did the first NY impulse do?
- Did price accept outside the opening range?
- Did price sweep and return?
- Was the first liquidity target already paid?
- Does the trade require a retest?
- Is a fresh entry now just chase?

Assessment quality effect:

- improves NY context and post-open patience
- weakens impulsive entries after the first move already expanded

Desired-state effect:

- sometimes, especially when deciding whether a 5m level is still current after the open

Rule:

- opening range is context, not an automatic ORB strategy

### 6. Risk/Expectancy = Trade Permission

What it reinforces:

- whether a technically correct idea has permission to become a trade

Allowed use:

- enforce invalidation-first thinking
- validate stop distance
- validate TP1 / TP2 / TP3 viability
- decide whether `ENTRY / SL / TP1 / TP2 / TP3` markup is allowed

Forbidden use:

- do not widen stops to make a trade fit
- do not modify the risk model
- do not change the TP ladder
- do not draw `ENTRY` markup if risk permission is invalid

Checklist:

- Where is structural invalidation?
- How much risk does the idea require?
- Does it fit `60-80` preferred?
- If it needs `100`, does the context clearly justify it?
- Is `TP1` reachable before major obstruction?
- Does the setup have permission or is it only understandable?

Assessment quality effect:

- keeps technically interesting ideas from being mislabeled as valid trades
- improves trade permission discipline

Desired-state effect:

- yes, it governs whether entry markup should be sent at all

Rule:

- a correct idea is not a permitted trade if risk does not fit the model

### 7. Psychology = Anti-Chase Discipline

What it reinforces:

- hard patience rules that already exist inside SMART MONEY / GOOD MONEY

Allowed use:

- enforce `WAIT` when edge is incomplete
- enforce `DO NOT CHASE` after triggered moves
- enforce `WAIT FOR NEW RETEST` when the opportunity already passed
- prevent expired setups from being repackaged as fresh

Forbidden use:

- do not add motivational filler
- do not produce vague psychology language with no trading action
- do not soften a hard `WAIT` into an optional suggestion

Checklist:

- Is the setup still ahead or already triggered?
- Did the first impulse already pay liquidity?
- Is a fresh entry now late?
- Is the correct action manage, wait, or do not chase?
- Is the system reusing an expired idea?

Assessment quality effect:

- improves action-state honesty
- prevents late execution from being framed as fresh edge

Desired-state effect:

- yes, it can block fresh 5m updates or entry markup when the setup is already late

Rule:

- `do not chase` is part of the strategy, not a soft suggestion
