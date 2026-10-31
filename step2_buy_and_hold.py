# Step 2: buy-and-hold baseline. Turns prices into daily returns and measures CAGR, volatility, Sharpe and max drawdown.
# The other steps import these functions, so every strategy is measured the same way.

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # the folder this file is in, so it runs from anywhere
DATA_DIR = os.path.join(BASE_DIR, "data")
PLOT_DIR = os.path.join(BASE_DIR, "plots")
ASSETS = ["WTI", "Gold"]
TRADING_DAYS = 252          # trading days in a year (the data has ~251.5)
RUN_PART_B = True          # True = also calculate and print the four metrics


def load_close(name: str) -> pd.Series:
    path = os.path.join(DATA_DIR, f"{name}.csv")

    df = pd.read_csv(path, index_col=0, parse_dates=True)   # first column (the dates) becomes the index, as real dates

    return df["Close"]


def daily_returns(close: pd.Series) -> pd.Series:
    r = close.pct_change().dropna()     # (today - yesterday) / yesterday; the first day has no yesterday, so it's dropped
    return r


def inspect_extremes(name: str, r: pd.Series) -> None:
    print(f"\n=== {name}: most extreme daily returns ===")
    lowest = r.nsmallest(3)     # the 3 worst days
    highest = r.nlargest(3)     # the 3 best days
    print("Worst 3 days:")
    print(lowest)
    print("Best 3 days:")
    print(highest)


def remove_bad_days(close: pd.Series) -> pd.Series:
    close = close.drop(pd.to_datetime(["2020-04-20"]), errors="ignore")   # removes WTI's -37.63 price (expiring May contract) before returns are calculated; "ignore" = do nothing for gold
    return close


def equity_curve(r: pd.Series) -> pd.Series:
    eq = (1 + r).cumprod()      # what £1 grows into: each day's value = yesterday's value x (1 + today's return)
    return eq


def cagr(equity: pd.Series) -> float:      # the steady yearly growth rate that gets from start to end value
    start = 1.0
    end = equity.iloc[-1]
    days = (equity.index[-1] - equity.index[0]).days    # calendar days between the first and last date
    years = days/365.25                                 # .25 accounts for leap years
    return (end/start)**(1/years) -1                    # ** (1/years) is the "years-th root"


def volatility(r: pd.Series) -> float:
    vol = r.std() * np.sqrt(252)        # daily std scaled to a year: variances add over days, so the std grows with sqrt(days)
    return vol


def sharpe(r: pd.Series) -> float:
    shar = (r.mean()/r.std()) * np.sqrt(252)    # return per unit of risk, per year; risk-free rate assumed 0
    return shar


def max_drawdown(equity: pd.Series) -> float:
    dd = equity / equity.cummax() - 1       # cummax = highest value so far, so this is "% below the best so far" each day
    return dd.min()                         # the worst fall from a peak


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    results = {}
    curves = {}

    for name in ASSETS:
        close = load_close(name)
        close = remove_bad_days(close)
        r = daily_returns(close)
        inspect_extremes(name, r)
        eq = equity_curve(r)
        curves[name] = eq
        print(f"{name}: £1 became £{eq.iloc[-1]:.2f}")

        if RUN_PART_B:
            results[name] = {
                "CAGR": cagr(eq),
                "Volatility": volatility(r),
                "Sharpe": sharpe(r),
                "Max drawdown": max_drawdown(eq),
            }

    if RUN_PART_B:
        table = pd.DataFrame(results).T     # .T flips it so each asset is a row
        print("\n=== Buy-and-hold baseline ===")
        print(table.to_string(float_format=lambda x: f"{x:.3f}"))

    fig, ax = plt.subplots(figsize=(11, 5))
    for name, eq in curves.items():
        ax.plot(eq.index, eq, label=name)
    ax.set_yscale("log")        # log scale: equal % moves look the same size, whatever the price level
    ax.set_title("Buy-and-hold: value of £1 (log scale)")
    ax.set_ylabel("£")
    ax.legend()
    plt.tight_layout()
    path = os.path.join(PLOT_DIR, "buy_and_hold.png")
    plt.savefig(path, dpi=150)
    print(f"\nSaved plot to {path}")
    plt.show()


if __name__ == "__main__":
    main()
