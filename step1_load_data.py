# Step 1: download daily WTI and gold prices, check them, save them as CSVs and plot them.

import os

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

TICKERS = {"WTI": "CL=F", "Gold": "GC=F"}   # my name for each asset -> its Yahoo Finance code
START = "2015-01-01"
END = "2026-01-01"                          # Yahoo stops the day BEFORE this, so the last day is 31 Dec 2025
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # the folder this file is in, so it runs from anywhere
DATA_DIR = os.path.join(BASE_DIR, "data")
PLOT_DIR = os.path.join(BASE_DIR, "plots")
COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def download_prices(ticker: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        start=START,
        end=END,
        auto_adjust=False,
        progress=False,
        multi_level_index=False,                # gives plain column names like "Close" instead of ("Close", "CL=F")
    )

    df = df[COLUMNS]            # keeps only the columns listed in COLUMNS

    df = df.dropna(subset = ['Close'])      # drops any row where "Close" is missing
    return df


def check_data(name: str, df: pd.DataFrame) -> None:
    print(f"\n=== {name} ===")

    days = df.shape[0]          # number of rows = number of trading days
    first_date = df.index[0]
    last_date = df.index[-1]    # -1 counts from the end, so this is the last date
    print(f"Trading days: {days}")
    print(f"The first date in the index is: {first_date}. The Last date in the index is: {last_date}")

    lowest_close = df["Close"].min()                    # the lowest closing price
    lowest_date = df["Close"].idxmin()                  # the DATE that lowest price happened on
    print(f"The lowest Close price: {lowest_close} and the Close date: {lowest_date}")

    numdays = (df["Close"]<=0).sum()        # True/False for each day; summing counts the Trues
    print(f"Number of Closes <=0: {numdays}")


def save_csv(name: str, df: pd.DataFrame) -> None:

    path = os.path.join(DATA_DIR, f"{name}.csv")        # e.g. .../data/WTI.csv
    df.to_csv(path)
    print(path)


def plot_prices(data: dict) -> None:
    fig, axes = plt.subplots(len(data), 1, figsize=(11, 7), sharex=True)   # one panel per asset, same date axis

    for ax, (name, df) in zip(axes, data.items()):      # pairs each panel with one asset
        ax.plot(df.index,df["Close"])
        ax.set_title(name)
        ax.set_ylabel("USD")

    axes[0].axhline(0, color="grey", linestyle="--", linewidth=0.8)   # dashed zero line so WTI's negative price stands out

    plt.tight_layout()
    path = os.path.join(PLOT_DIR, "prices.png")
    plt.savefig(path, dpi=150)
    print(f"\nSaved plot to {path}")
    plt.show()


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)    # creates the folder if it doesn't exist yet
    os.makedirs(PLOT_DIR, exist_ok=True)

    data = {}
    for name, ticker in TICKERS.items():
        df = download_prices(ticker)
        check_data(name, df)
        save_csv(name, df)
        data[name] = df

    plot_prices(data)


if __name__ == "__main__":      # only runs main() when this file is run directly, not when imported
    main()
