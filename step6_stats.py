# Step 6: are any strategies really different from buy-and-hold?
# Paired t-test on the daily differences (strategy - buy & hold) for each of the 6 strategy/asset pairs,
# with Bonferroni and Holm corrections because 6 tests are run at once.

import os

import numpy as np
import pandas as pd
from scipy import stats

from step2_buy_and_hold import ASSETS, TRADING_DAYS, load_close, remove_bad_days, daily_returns
from step3_momentum import momentum_signal, to_position, strategy_returns
from step4_mean_reversion import zscore, signal_vectorised
from step5_trend_following import moving_averages, trend_signal

ALPHA = 0.05
N_TESTS = 6
ALPHA_BONF = ALPHA / N_TESTS          # Bonferroni: share the 5% across 6 tests, ≈ 0.0083 each
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")


def all_strategies() -> dict:      # rebuilds all 6 strategies exactly as in steps 3–5
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
            strat = strategy_returns(to_position(sig), r)
            out[(name, label)] = (strat, r.loc[strat.index])          # (strategy returns, buy-and-hold returns on the same dates)
    return out


def differences(strat: pd.Series, bh: pd.Series) -> pd.Series:
    dd = strat - bh             # each day: how much better (or worse) the strategy did than buy-and-hold
    return dd


def t_by_hand(d: pd.Series) -> float:
    se = d.std()/np.sqrt(len(d))    # standard error: how much the average difference would wobble by chance
    ttest = d.mean() /se            # how many standard errors the average difference is from 0
    return ttest


def t_and_p_scipy(strat: pd.Series, bh: pd.Series) -> tuple:
    t,p =stats.ttest_rel(strat, bh)     # scipy's paired t-test (two-sided); should match t_by_hand
    return t, p


def information_ratio(d: pd.Series) -> float:
    return (d.mean() * np.sqrt(252))/d.std()     # Sharpe ratio of the differences, per year; t ≈ this x sqrt(years)


def holm(pvalues: pd.Series, alpha: float = ALPHA) -> pd.Series:    # Holm-Bonferroni: same 5% guarantee as Bonferroni but less strict
    m = len(pvalues)
    result = pd.Series(False, index=pvalues.index)              # everything starts as "not significant"
    for k, (label, p) in enumerate(pvalues.sort_values().items()):     # smallest p first; k = 0, 1, 2, ...
        if (p < alpha /(m-k)):      # bar loosens each step: alpha/6, alpha/5, alpha/4, ...
            result[label] = True
        else:
            result[label] = False
            break                   # stop at the first failure: this and all larger p-values stay not significant
    return result


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = []

    for (asset, label), (strat, bh) in all_strategies().items():
        d = differences(strat, bh)
        t_hand = t_by_hand(d)
        t_sci, p = t_and_p_scipy(strat, bh)

        rows.append({
            "Asset": asset,
            "Strategy": label,
            "Mean diff (%/yr)": d.mean() * TRADING_DAYS * 100,     # average daily difference, as % per year
            "Info ratio": information_ratio(d),
            "t (by hand)": t_hand,
            "t (scipy)": t_sci,
            "p-value": p,
            "Sig at 0.05": (p - ALPHA) < 0,             # True if p is below 0.05
            "Sig after Bonf.": (p - ALPHA_BONF) < 0,    # True if p is below 0.05 / 6
        })

    table = pd.DataFrame(rows).set_index(["Asset", "Strategy"])
    table["Sig (Holm)"] = holm(table["p-value"])
    print(f"\n=== Paired t-tests vs buy & hold (Bonferroni alpha = {ALPHA_BONF:.4f}) ===")
    print(table.to_string(float_format=lambda x: f"{x:.4f}"))

    n_raw = int(table["Sig at 0.05"].sum()) if "Sig at 0.05" in table else "?"     # summing True/False counts the Trues
    n_bonf = int(table["Sig after Bonf."].sum()) if "Sig after Bonf." in table else "?"
    n_holm = int(table["Sig (Holm)"].sum())
    print(f"\nSignificant at 0.05: {n_raw} of {N_TESTS}.  After Bonferroni: {n_bonf} of {N_TESTS}."
          f"  After Holm: {n_holm} of {N_TESTS}.")

    path = os.path.join(RESULTS_DIR, "stats.csv")
    table.to_csv(path)
    print(f"Saved table to {path}")


if __name__ == "__main__":
    main()
