"""Hybrid two-mode dip bot for make.fun btc-race-24h-20261118-1444.

Trades cbBTC/USDC 1-minute bars, long only, starting from 1,000 USDC paper.
The dev window (24h, BTC -2.80%, range 63,076-65,190) is a falling,
choppy tape: shallow-dip and rolling-high dip-buying LOSE on it (they buy
into the grind and bleed on fees: -11 to -19 USDC), momentum ignition
LOSES (-4 to -17 USDC), and the slow-EMA dip ladder that won yesterday
only makes +2 to +9 USDC. What pays is buying a genuine excursion.

Two legs, one open position at most, deep checked first:

DEEP leg -- the proven v1 rule, at its plateau-best hold. Buy the FULL
cash when the close is 1.6% below the highest close of the last 300
minutes (no deep trades until 302 closes have been seen), then sell the
bounce at +1.8% over the average entry, or -1.2% stop, or after 360 bars.
Two round trips on the dev window, both winners.

MID leg -- race insurance. The one reactive signal with a real edge on
this tape is a dip vs SMA20 of >= 28 bps together with a green bar
(close above the previous close): mean forward return +37 bps at 15
bars. Buy 25% of cash on it, take profit at +0.40% over the average
entry, no stop-loss, max hold 20 bars. It trades when the tape offers
no 1.6% excursion, so the bot still trades instead of scoring 0 trades.

Both legs stop opening at/after bar 1380 (60 bars left in the window)
and cap slippage at 200 bps. All decisions are pure functions of the
bar stream: no clock, no environment, no randomness, so two runs agree
byte for byte. Entry price is the position's average cost from the
account state (never an assumed price), and exits compare in integer
basis points against that average cost.

Local replay on the frozen dev window: net PnL +$26.17, 12 trades
(6 round trips, all winners), max drawdown 0.65%.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = None  # set from hello: the competition's single symbol

# DEEP leg: 300-bar rolling-high dip, full cash.
DEEP_LOOKBACK = 300  # rolling-high window: 300 one-minute closes (~5 hours)
DEEP_DIP = 0.016  # buy when the close is this far below the 300-bar high
DEEP_TP_BPS = 180  # sell when close is this far above the average entry
DEEP_SL_BPS = 120  # sell when close is this far below the average entry
DEEP_MAX_HOLD = 360  # sell after this many bars held, whatever the price
DEEP_WARMUP = 302  # no deep trades until this many closes have been seen

# MID leg: SMA20 dip + green bar, 25% of cash.
MID_SMA_LEN = 20  # SMA window: mean of the last 20 closes (integer division)
MID_DIP_BPS = 28  # buy when (SMA20 - close) is at least this many bps of SMA20
MID_TP_BPS = 40  # sell when close is this far above the average entry
MID_MAX_HOLD = 20  # sell after this many bars held, whatever the price
# MID has no stop-loss: it exits on take-profit or max hold only.

MAX_SLIPPAGE_BPS = 200  # 2%: covers the largest 1-minute move seen (~0.65%)
NO_BUY_AFTER_BARS = 1380  # stop opening with 60 bars left in the window

_closes = []  # closes of scored bars, oldest first
_buy_bar = 0  # scored bar of the buy that opened the position
_mode = None  # "deep" or "mid": which leg opened the open position


def on_hello(state):
    global SYMBOL
    SYMBOL = state.hello["symbols"][0]["symbol"]


def _avg_entry_price(state):
    """Average entry price of the open position, in raw price units.

    cost is quote units spent, qty is qty-scale units: avg = cost * 10**7
    // qty. (cost * 10**13 // (qty * 10**6) is the same number.)
    """
    holding = state.positions.get(SYMBOL)
    if holding is None or holding.qty <= 0:
        return None
    return holding.cost * 10 ** 7 // holding.qty


def on_batch(state, batch):
    global _buy_bar, _mode
    if state.warming_up:
        return []
    bar = None
    for b in batch.get("bars", []):
        if b.get("symbol") == SYMBOL:
            bar = b
            break
    if bar is None:
        return []
    close = int(bar["c"])
    _closes.append(close)

    holding = state.positions.get(SYMBOL)
    if holding is not None and holding.qty > 0:
        # Holding: exit by the mode of the entry that opened the position.
        avg = _avg_entry_price(state)
        if avg is not None:
            if _mode == "mid":
                tp_bps = MID_TP_BPS
                sl_bps = None
                max_hold = MID_MAX_HOLD
            else:
                tp_bps = DEEP_TP_BPS
                sl_bps = DEEP_SL_BPS
                max_hold = DEEP_MAX_HOLD
            if close * 10000 >= avg * (10000 + tp_bps):
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            if sl_bps is not None and close * 10000 <= avg * (10000 - sl_bps):
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            if state.seq - _buy_bar >= max_hold:
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    # Flat: at most one open position; deep branch first (priority).
    if state.seq >= NO_BUY_AFTER_BARS:
        return []

    # DEEP: close 1.6% below the highest close of the last 300 bars.
    if len(_closes) >= DEEP_WARMUP:
        high = max(_closes[-DEEP_LOOKBACK:])
        if close <= high * (1.0 - DEEP_DIP):
            _buy_bar = state.seq
            _mode = "deep"
            notional = state.cash
            if notional >= 1_000_000:
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": notional,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS,
                         "client_id": state.client_id()}]
            return []

    # MID: dip vs SMA20 >= 28 bps AND a green bar, 25% of cash.
    if len(_closes) >= MID_SMA_LEN:
        sma20 = sum(_closes[-MID_SMA_LEN:]) // MID_SMA_LEN
        dip = (sma20 - close) * 10000 // sma20
        if dip >= MID_DIP_BPS and close > _closes[-2]:
            _buy_bar = state.seq
            _mode = "mid"
            notional = state.cash // 4
            if notional >= 1_000_000:
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": notional,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS,
                         "client_id": state.client_id()}]
    return []


makefun_bars.run(on_batch, on_hello=on_hello)
