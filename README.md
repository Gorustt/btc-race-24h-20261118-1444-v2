[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Gorustt/btc-race-24h-20261118-1444-v2/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Gorustt/btc-race-24h-20261118-1444-v2/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

# Hybrid Two-Mode Dip Bot — btc-race-24h-20261118-1444

A bot that trades cbBTC/USDC on 1-minute bars for make.fun's
"Race a BTC trading bot live for 24 hours" competition ($250, top 10 paid).
Version 2 of the v1 V-bottom dip bot: the same deep-dip rule at its
plateau-best hold, plus a small selective mid leg so the bot still trades
when the race window offers no deep excursion.

Strategy (long only, $1,000 USDC paper start, at most 1 open position,
deep branch checked first):

- DEEP leg: buy the full cash when the close is 1.6% below the highest
  close of the last 300 minutes (no deep trades until 302 closes seen).
  Sell at +1.8% over the average entry, or -1.2% stop, or after 360 bars.
- MID leg: buy 25% of cash when the close is at least 28 bps below its
  20-bar SMA *and* the bar is green (close above the previous close).
  Sell at +0.40% over the average entry, or after 20 bars. No stop-loss.
- Both legs: max slippage 200 bps, no new buys at/after bar 1380.
  All decisions are pure functions of the bar stream (no clock, no
  environment, no randomness); exits compare in integer basis points
  against the position's average cost. Standard library only, plus the
  vendored kit SDK shim under `vendor/`.

Local replay on the frozen dev window: net PnL +$26.17, 12 trades
(6 round trips, all winners), max drawdown 0.65%. This beats v1's
+$22.51 (2 round trips): the longer deep hold adds +$1.87 and the mid
leg adds 4 round trips worth +$1.79.

Run: `python3 -P -s main.py` (Python 3.13, stdlib only).
Protocol: agent-fun/bars-replay/v1.

---

<sub>Entered on [make.fun](https://make.fun/?ref=vjg8d7r1&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
