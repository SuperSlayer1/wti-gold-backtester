# Step 3: 20-day momentum. Long tomorrow if today's price is above its price 20 days ago, otherwise flat.

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from step2_buy_and_hold import (       # reuses step 2's functions so every strategy is measured the same way
    ASSETS, PLOT_DIR, TRADING_DAYS,
    load_close, remove_bad_days, daily_returns, equity_curve,
    cagr, volatility, sharpe, max_drawdown,
)

LOOKBACK = 20       # chosen before testing and not tuned, to avoid overfitting


def momentum_signal(close: pd.Series) -> pd.Series:
    momentum = (close.pct_change(20) > 0).astype(int)    # 20-day return > 0? True/False -> 1/0; the first 20 days are NaN, which count as False (flat)
    return momentum


def to_position(signal: pd.Series) -> pd.Series:
    to_pos = signal.shift(1).fillna(0)     # today's signal is only known after the close, so it's traded TOMORROW; day one has no position
    return to_pos


def strategy_returns(position: pd.Series, r: pd.Series) -> pd.Series:
    return (position * r).dropna()      # earns the day's return when long (1), nothing when flat (0); pandas matches the two by date


def exposure(position: pd.Series) -> float:
    return position.mean()      # the mean of 1s and 0s = fraction of days in the market


def trades_per_year(position: pd.Series) -> float:
    days = (position.index[-1] - position.index[0]).days
    return (position.diff().abs().sum())/(days/365.25)     # each change of position (in or out) counts as one trade


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    rows = {}
    fig, axes = plt.subplots(len(ASSETS), 1, figsize=(11, 7), sharex=True)

    for ax, name in zip(axes, ASSETS):
        close = remove_bad_days(load_close(name))
        r = daily_returns(close)

        signal = momentum_signal(close)
        pos = to_position(signal)
        strat = strategy_returns(pos, r)

        bh = r.loc[strat.index]     # buy-and-hold on exactly the same dates, for a fair comparison

        for label, rets in [("Buy & hold", bh), ("Momentum", strat)]:
            eq = equity_curve(rets)
            rows[(name, label)] = {
                "CAGR": cagr(eq),
                "Volatility": volatility(rets),
                "Sharpe": sharpe(rets),
                "Max drawdown": max_drawdown(eq),
            }
            ax.plot(eq.index, eq, label=label)

        rows[(name, "Momentum")]["Exposure"] = exposure(pos.loc[strat.index])
        rows[(name, "Momentum")]["Trades/yr"] = trades_per_year(pos.loc[strat.index])

        ax.set_yscale("log")
        ax.set_title(f"{name}: {LOOKBACK}-day momentum vs buy & hold")
        ax.set_ylabel("£ (log)")
        ax.legend()

    table = pd.DataFrame(rows).T
    print(f"\n=== {LOOKBACK}-day momentum vs buy & hold ===")
    print(table.to_string(float_format=lambda x: f"{x:.3f}", na_rep="—"))     # na_rep shows blank cells as a dash

    plt.tight_layout()
    path = os.path.join(PLOT_DIR, "momentum.png")
    plt.savefig(path, dpi=150)
    print(f"\nSaved plot to {path}")
    plt.show()


if __name__ == "__main__":
    main()
