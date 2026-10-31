# Step 5: trend following. Long while the 50-day average price is above the 200-day average, otherwise flat.

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
from step4_mean_reversion import hit_rate

FAST = 50       # 50/200 is the standard textbook pair, not tuned to this data
SLOW = 200


def moving_averages(close: pd.Series) -> tuple:
    fast = close.rolling(FAST).mean()       # average price over the last 50 days, recalculated every day
    slow = close.rolling(SLOW).mean()       # same over 200 days (blank for the first 199 days)
    return fast, slow                       # returns both at once


def trend_signal(fast: pd.Series, slow: pd.Series) -> pd.Series:
    return (fast > slow).astype(int)        # 1 when the fast average is above the slow one; blank days compare as False, so flat during the warm-up


def avg_holding_days(pos: pd.Series) -> float:
    return pos.sum()/(pos.diff() == 1).sum() if (pos.diff() == 1).sum() else np.nan   # days in the market / number of entries (0 -> 1); nan if it never traded


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    rows = {}
    fig, axes = plt.subplots(len(ASSETS), 2, figsize=(14, 7))     # left: equity curves, right: price and averages

    for (ax_eq, ax_px), name in zip(axes, ASSETS):
        close = remove_bad_days(load_close(name))
        r = daily_returns(close)

        fast, slow = moving_averages(close)
        sig = trend_signal(fast, slow)
        pos = to_position(sig)
        strat = strategy_returns(pos, r)
        bh = r.loc[strat.index]
        pos = pos.loc[strat.index]

        for label, rets in [("Buy & hold", bh), ("Trend 50/200", strat)]:
            eq = equity_curve(rets)
            rows[(name, label)] = {
                "CAGR": cagr(eq),
                "Volatility": volatility(rets),
                "Sharpe": sharpe(rets),
                "Max drawdown": max_drawdown(eq),
                "Skew": rets.skew(),
            }
            ax_eq.plot(eq.index, eq, label=label)

        rows[(name, "Trend 50/200")]["Exposure"] = exposure(pos)
        rows[(name, "Trend 50/200")]["Trades/yr"] = trades_per_year(pos)
        rows[(name, "Trend 50/200")]["Hit rate"] = hit_rate(strat, pos)
        rows[(name, "Trend 50/200")]["Avg hold (days)"] = avg_holding_days(pos)

        ax_eq.set_yscale("log")
        ax_eq.set_title(f"{name}: value of £1 (log)")
        ax_eq.legend()

        ax_px.plot(close.index, close, label="Close", linewidth=0.8, alpha=0.6)   # price with both averages, to see the crossovers
        ax_px.plot(fast.index, fast, label=f"{FAST}-day avg")
        ax_px.plot(slow.index, slow, label=f"{SLOW}-day avg")
        ax_px.set_title(f"{name}: price and moving averages")
        ax_px.legend()

    table = pd.DataFrame(rows).T
    print(f"\n=== Trend following ({FAST}/{SLOW} crossover) vs buy & hold ===")
    print(table.to_string(float_format=lambda x: f"{x:.3f}", na_rep="—"))

    plt.tight_layout()
    path = os.path.join(PLOT_DIR, "trend_following.png")
    plt.savefig(path, dpi=150)
    print(f"\nSaved plot to {path}")
    plt.show()


if __name__ == "__main__":
    main()
