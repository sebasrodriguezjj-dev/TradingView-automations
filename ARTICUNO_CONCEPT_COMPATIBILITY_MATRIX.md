# Articuno Concept Compatibility Matrix

This matrix makes Articuno reinforcement operational without letting it become a second strategy.

## HARD REINFORCEMENT

| Concept | Source Family | Reinforcement Lens | Allowed Use | Forbidden Use | Liquidity | Level | Trigger | Timing | Risk | Desired State | Communication |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Buy-side liquidity | SMC | SMC | Clarify nearest upside objective or trap | Standalone long/short signal | Yes | No | Yes | Yes | No | Yes | No |
| Sell-side liquidity | SMC | SMC | Clarify nearest downside objective or trap | Standalone long/short signal | Yes | No | Yes | Yes | No | Yes | No |
| Liquidity sweep | SMC | SMC | Confirm that a target was attacked before reclaim/rejection analysis | Trade just because a sweep printed | Yes | No | Yes | Yes | No | Yes | No |
| Post-sweep reclaim | SMC / PA | SMC / Price Action | Strengthen an existing thesis when acceptance confirms | Override HTF or create a fresh setup alone | Yes | No | Yes | Yes | No | Yes | No |
| Post-sweep rejection | SMC / PA | SMC / Price Action | Strengthen failed-break or fade quality | Trade from wick-only without thesis | Yes | No | Yes | Yes | No | Yes | No |
| Liquidity already paid | SMC / Psychology | SMC / Psychology | Block late entries and improve `TRIGGERED / EXPIRED` honesty | Ignore and keep calling the setup fresh | Yes | No | Yes | Yes | No | Yes | Yes |
| Fresh vs tested supply/demand | Supply/Demand | Supply/Demand | Judge whether a level deserves to stay active | Keep weak mitigated levels as primary map | No | Yes | Yes | Yes | No | Yes | No |
| Displacement-origin zone | Supply/Demand | Supply/Demand | Improve structural quality of a level | Treat as standalone entry system | No | Yes | Yes | No | No | Yes | No |
| Flip zone | Supply/Demand | Supply/Demand | Clarify when a reclaimed level can change role | Promote random flips with no structure | No | Yes | Yes | Yes | No | Yes | No |
| Effort vs result at key level | VPA | VPA | Confirm or question quality of reaction | Trade from volume alone | No | No | Yes | Yes | No | No | Yes |
| Failed continuation after sweep | VPA / PA | VPA / Price Action | Strengthen rejection or failed breakout read | Replace thesis hierarchy with VPA | Yes | No | Yes | Yes | No | Yes | No |
| Clean retest | Price Action | Price Action | Confirm execution quality after reclaim/rejection | Treat every revisit as clean retest | No | Yes | Yes | Yes | No | Yes | No |
| Failed retest | Price Action | Price Action | Confirm tactical failure or continuation | Ignore HTF context and scalp against thesis | No | Yes | Yes | Yes | No | Yes | No |
| Reclaim acceptance | Price Action | Price Action | Confirm that a level truly held after reclaim | Call first poke an accepted reclaim | No | Yes | Yes | Yes | No | Yes | No |
| First NY impulse already ran | Opening Range | Opening Range | Detect chase risk after the open | Turn into automatic ORB trading | Yes | No | Yes | Yes | No | Yes | Yes |
| Risk-fit gate | Risk/Expectancy | Risk/Expectancy | Decide if a valid idea may become a trade | Stretch stops to force permission | No | No | No | No | Yes | Yes | No |
| Invalidation-first trade planning | Risk/Expectancy | Risk/Expectancy | Start from structural invalidation before entry | Entry-first planning with stop retrofitted later | No | No | Yes | No | Yes | Yes | No |
| DO NOT CHASE | Psychology | Psychology | Enforce post-trigger discipline | Treat as optional tone note | No | No | No | Yes | Yes | Yes | Yes |
| WAIT FOR NEW RETEST | Psychology / PA | Psychology / Price Action | Preserve patience after the first move already ran | Repackage expired entry as fresh | No | No | Yes | Yes | No | Yes | Yes |

## SOFT CONFIRMATION

| Concept | Source Family | Reinforcement Lens | Allowed Use | Forbidden Use | Liquidity | Level | Trigger | Timing | Risk | Desired State | Communication |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BOS | Structure | Price Action | Support a structure shift already aligned with thesis | Treat as standalone signal | No | No | Yes | Yes | No | No | No |
| CHoCH | Structure | Price Action | Support that micro structure changed | Let micro CHoCH override HTF | No | No | Yes | Yes | No | No | No |
| Inducement | SMC | SMC | Clarify how liquidity may be baited before the real move | Build trades only from inducement theory | Yes | No | Yes | Yes | No | No | No |
| Premium/discount | SMC | SMC | Help frame better location inside existing thesis | Trade from premium/discount alone | Yes | Yes | No | No | No | No | No |
| Compression into level | Price Action | Price Action | Raise attention around a likely reaction shelf | Assume compression guarantees breakout | No | Yes | Yes | Yes | No | Yes | No |
| Wick rejection | Price Action | Price Action | Add confidence to a broader rejection story | Trade from a single wick alone | No | No | Yes | Yes | No | No | No |
| Volume drying on pullback | VPA | VPA | Support pullback quality or lack of pressure | Use as standalone entry trigger | No | No | Yes | Yes | No | No | No |
| Opening range high/low | Opening Range | Opening Range | Provide NY context and chase-risk framing | Buy/sell every OR high/low break | Yes | Yes | Yes | Yes | No | Yes | No |
| Micro HH/HL or LH/LL | Structure | Price Action | Refine 5m trigger quality within the thesis | Let micro tape override HTF | No | No | Yes | Yes | No | No | No |
| Tape-reading proxies | VPA / PA | VPA / Price Action | Add color to participation or exhaustion reads | Use as predictive standalone signals | No | No | Yes | Yes | No | No | Yes |
| Order blocks | SMC | Supply/Demand | Use only as extra confluence when already tied to structure and liquidity | Standalone OB entries or new drawing types | No | Yes | Yes | No | No | No | No |
| FVG / imbalance | SMC | Supply/Demand | Use only as extra confluence around an existing level | Standalone FVG entries or rectangles | No | Yes | Yes | No | No | No | No |
| Trendlines | Structure | Price Action | Use only as very soft context if they support the real thesis | Turn into a trendline system | No | No | No | No | No | No | No |
| Divergence | Indicator / PA | Price Action | Use only as weak caution or confidence note | Create trades from divergence | No | No | No | No | No | No | Yes |
| Volume spikes | VPA | VPA | Support effort-vs-result review | Use spikes alone as signals | No | No | Yes | No | No | No | Yes |
| Single candle rejection | Price Action | Price Action | Add soft confirmation to a broader story | Standalone one-candle entries | No | No | Yes | No | No | No | No |

## COACHING ONLY

| Concept | Source Family | Reinforcement Lens | Allowed Use | Forbidden Use | Liquidity | Level | Trigger | Timing | Risk | Desired State | Communication |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Patience after first impulse | Psychology | Psychology | Remind why waiting improves execution | Turn into vague filler with no action | No | No | No | Yes | No | No | Yes |
| Correction before continuation | Price Action | Price Action | Explain why not to chase the first expansion | Use as a new setup family | No | No | Yes | Yes | No | No | Yes |
| Contradictory timeframe caution | Structure | Psychology | Explain why the engine says `WAIT / NO CLEAR EDGE` | Override the existing hierarchy | No | No | No | Yes | No | No | Yes |
| Late-but-correct idea | Psychology | Psychology | Explain difference between good thesis and bad timing | Repackage late ideas as valid entries | No | No | No | Yes | No | No | Yes |

## IGNORE / NOT COMPATIBLE

| Concept | Source Family | Reinforcement Lens | Allowed Use | Forbidden Use | Liquidity | Level | Trigger | Timing | Risk | Desired State | Communication |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Standalone OB/FVG entries | SMC | None | None | New strategy, new drawings, standalone entries | No | No | No | No | No | No | No |
| Standalone ORB entries | Opening Range | None | None | Automatic open-breakout strategy | No | No | No | No | No | No | No |
| Standalone VPA entries | VPA | None | None | Volume-only trades | No | No | No | No | No | No | No |
| Standalone trendline trades | Structure | None | None | Trendline-based system | No | No | No | No | No | No | No |
| Indicator scalping systems | Indicators | None | None | Strategy drift away from SMART MONEY / GOOD MONEY | No | No | No | No | No | No | No |
| Options-specific strategies | Derivatives | None | None | Outside instrument and workflow scope | No | No | No | No | No | No | No |
| Pure prediction models | Prediction | None | None | Bypass structure, liquidity, and execution discipline | No | No | No | No | No | No | No |
| AI signals that bypass the strategy | AI | None | None | Override the existing engine with black-box calls | No | No | No | No | No | No | No |
