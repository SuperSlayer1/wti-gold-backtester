# Step 4: mean reversion. Buy when the price is unusually low compared with its last 20 days (z < -1),
# hold until it's back to its 20-day average (z >= 0), then go flat.

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from step2_buy_and_hold import (
    ASSETS, PLOT_DIR,
    load_close, remove_bad_days, daily_returns, equity_curve,
    cagr, volatility, sharpe, max_drawdown,
)
from step3_momentum import to_position, strategy_returns, exposure, trades_per_year

WINDOW = 20      # days used for the rolling mean and std (chosen before testing, not tuned)
ENTRY_Z = -1.0   # go long when z drops below this
EXIT_Z = 0.0     # go flat when z gets back to this


def zscore(close: pd.Series) -> pd.Series:
    z = (close - close .rolling(WINDOW).mean())/ close.rolling(WINDOW).std()   # how many recent std's today's price is from its 20-day average; only uses past data
    return z


def signal_loop(z: pd.Series) -> pd.Series:
    holding = 0                 # 0 = flat, 1 = long; carried from one day to the next
    out = []
    for value in z:             # goes through the z-scores in date order
        if holding == 0 and value < ENTRY_Z:       # flat and the price is unusually low -> buy
            holding = 1
        elif holding == 1 and value >= EXIT_Z:     # long and the price is back to normal -> sell
            holding = 0
        out.append(holding)     # otherwise keep yesterday's position
    return pd.Series(out, index=z.index)


def signal_vectorised(z: pd.Series) -> pd.Series:      # same result as signal_loop, done the pandas way
    events = pd.Series(np.nan, index=z.index)       # starts as "nothing happened" on every day
    events[z < ENTRY_Z] = 1                         # mark the entry days
    events[z >= EXIT_Z] = 0                         # mark the exit days
    return events.ffill().fillna(0).astype(int)     # ffill carries the last entry/exit forward over the quiet days; before any event = flat


def hit_rate(strat: pd.Series, pos: pd.Series) -> float:
    return (strat[pos == 1] > 0).mean()     # of the days in the market, the fraction that made money


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    rows = {}
    fig, axes = plt.subplots(len(ASSETS), 1, figsize=(11, 7), sharex=True)

    for ax, name in zip(axes, ASSETS):
        close = remove_bad_days(load_close(name))
        r = daily_returns(close)

        z = zscore(close)
        sig = signal_loop(z)
        sig_fast = signal_vectorised(z)
        same = sig.equals(sig_fast)     # check: both versions must give exactly the same signal
        print(f"{name}: loop and vectorised signals identical? {same}")

        pos = to_position(sig)
        strat = strategy_returns(pos, r)
        bh = r.loc[strat.index]
        pos = pos.loc[strat.index]

        for label, rets in [("Buy & hold", bh), ("Mean reversion", strat)]:
            eq = equity_curve(rets)
            rows[(name, label)] = {
                "CAGR": cagr(eq),
                "Volatility": volatility(rets),
                "Sharpe": sharpe(rets),
                "Max drawdown": max_drawdown(eq),
                "Skew": rets.skew()     # negative = rare big losses, positive = rare big gains
            }
            ax.plot(eq.index, eq, label=label)

        rows[(name, "Mean reversion")]["Exposure"] = exposure(pos)
        rows[(name, "Mean reversion")]["Trades/yr"] = trades_per_year(pos)
        rows[(name, "Mean reversion")]["Hit rate"] = hit_rate(strat, pos)

        ax.set_yscale("log")
        ax.set_title(f"{name}: mean reversion (z < {ENTRY_Z} in, z ≥ {EXIT_Z} out) vs buy & hold")
        ax.set_ylabel("£ (log)")
        ax.legend()

    table = pd.DataFrame(rows).T
    print(f"\n=== Mean reversion ({WINDOW}-day z-score) vs buy & hold ===")
    print(table.to_string(float_format=lambda x: f"{x:.3f}", na_rep="—"))

    plt.tight_layout()
    path = os.path.join(PLOT_DIR, "mean_reversion.png")
    plt.savefig(path, dpi=150)
    print(f"\nSaved plot to {path}")
    plt.show()


if __name__ == "__main__":
    main()
