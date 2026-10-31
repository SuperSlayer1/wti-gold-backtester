# Step 7: transaction costs. Charges c basis points every time a position changes,
# then finds each strategy's break-even cost: the cost per trade at which its lead over buy-and-hold disappears.


import os

import numpy as np
import pandas as pd

from step2_buy_and_hold import (
    ASSETS, TRADING_DAYS, load_close, remove_bad_days, daily_returns,
    equity_curve, cagr, sharpe,
)
from step3_momentum import momentum_signal, to_position, strategy_returns, trades_per_year
from step4_mean_reversion import zscore, signal_vectorised
from step5_trend_following import moving_averages, trend_signal

COST_LEVELS_BP = [0, 2, 5, 10, 20]   # costs to test, in basis points per position change (1 bp = 0.01%)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")



def all_positions() -> dict:       # rebuilds the 6 strategies' daily positions (0 or 1) as in steps 3–5
    out = {}
    for name in ASSETS:
        close = remove_bad_days(load_close(name))
        r = daily_returns(close)
        signals = {
            "Momentum": momentum_signal(close),
            "Mean reversion": signal_vectorised(zscore(close)),
            "Trend 50/200": trend_signal(*moving_averages(close)),     # * unpacks (fast, slow) into the two arguments
        }
        for label, sig in signals.items():
            pos = to_position(sig).loc[r.index]   # same dates as the returns
            out[(name, label)] = (pos, r)
    return out


def trading_costs(pos: pd.Series, cost_bp: float) -> pd.Series:
    c = cost_bp * 0.0001                        # basis points -> fraction (5 bp = 0.0005)
    return c * pos.diff().abs().fillna(0)       # cost only on days the position changes; day one counts as no change


def net_returns(pos: pd.Series, r: pd.Series, cost_bp: float) -> pd.Series:

    return (strategy_returns(pos, r) - trading_costs(pos, cost_bp)).dropna()   # returns before costs minus that day's cost


def breakeven_formula(pos: pd.Series, r: pd.Series) -> float:     # approximate break-even in bp: lead over buy-and-hold / yearly cost of 1 bp
    gross = strategy_returns(pos, r)
    bh = r.loc[gross.index]
    gap = (cagr(equity_curve(gross)) - cagr(equity_curve(bh)))     # how far ahead of buy-and-hold per year, before costs
    tpy = (trades_per_year(pos.loc[gross.index]) * 0.0001)        # how much each 1 bp of cost takes off per year
    if gap <= 0 or tpy == 0:        # never ahead (or never trades): no break-even to find
        return np.nan
    else:
        return gap / tpy


def breakeven_search(pos: pd.Series, r: pd.Series, max_bp: float = 500, step: float = 0.5) -> float:  # exact break-even, to check the formula
    gross = strategy_returns(pos, r)
    bh_cagr = cagr(equity_curve(r.loc[gross.index]))
    if cagr(equity_curve(gross)) <= bh_cagr:
        return np.nan
    for bp in np.arange(0, max_bp + step, step):    # tries 0, 0.5, 1, 1.5, ... bp
        net = net_returns(pos, r, bp)
        if cagr(equity_curve(net)) <= bh_cagr:      # the first cost where the strategy is no longer ahead
            return bp
    return np.inf                                   # still ahead even at max_bp


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = []

    for (asset, label), (pos, r) in all_positions().items():
        gross = strategy_returns(pos, r)
        bh = r.loc[gross.index]
        row = {
            "Asset": asset,
            "Strategy": label,
            "Trades/yr": trades_per_year(pos.loc[gross.index]),
            "B&H CAGR": cagr(equity_curve(bh)),
        }
        for bp in COST_LEVELS_BP:
            net = net_returns(pos, r, bp)
            row[f"CAGR @{bp}bp"] = cagr(equity_curve(net))
            row[f"Sharpe @{bp}bp"] = sharpe(net)
        row["Break-even bp (formula)"] = breakeven_formula(pos, r)
        row["Break-even bp (exact)"] = breakeven_search(pos, r)
        rows.append(row)

    table = pd.DataFrame(rows).set_index(["Asset", "Strategy"])

    cagr_cols = ["Trades/yr", "B&H CAGR"] + [f"CAGR @{bp}bp" for bp in COST_LEVELS_BP]     # builds the column names for each cost level
    sharpe_cols = [f"Sharpe @{bp}bp" for bp in COST_LEVELS_BP]
    be_cols = ["Break-even bp (formula)", "Break-even bp (exact)"]

    fmt = lambda x: f"{x:.3f}"      # print numbers to 3 decimal places
    print("\n=== CAGR after costs ===")
    print(table[cagr_cols].to_string(float_format=fmt))
    print("\n=== Sharpe after costs ===")
    print(table[sharpe_cols].to_string(float_format=fmt))
    print("\n=== Break-even cost vs buy & hold (bp per position change; '—' = never ahead) ===")
    print(table[be_cols].to_string(float_format=lambda x: f"{x:.1f}", na_rep="—"))

    path = os.path.join(RESULTS_DIR, "costs.csv")
    table.to_csv(path)
    print(f"\nSaved table to {path}")


if __name__ == "__main__":
    main()
