from yahooquery import Ticker
import datetime
import pandas as pd
import warnings
import sys

warnings.simplefilter(action='ignore', category=FutureWarning)

# Get tickers
def get_tickers():
    filename = 'screeners/nasdaq.csv'

    tickers=[]
    with open(filename, "r") as csvfile:
        # Skip the header line (assuming the first line contains headers)
        next(csvfile)  # Skip the first line

        for line in csvfile:
        # Extract the first element (assuming it's the ticker symbol)
            tickers.append(line.strip().split(",")[0])
    tickers.append("COMP")
    return tickers

# Set options to show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

# Calculate the date range for the last n days
end_date = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d")
start_date = datetime.datetime.strptime(sys.argv[2], "%Y-%m-%d")

# Download stock data
tickers = get_tickers()
# print(tickers)
ticker_data = Ticker(tickers, asynchronous=True)
# ticker_data = Ticker("IESC COMP", asynchronous=True)
data = ticker_data.history(start=start_date, end=end_date, interval='1d')
data.to_csv('backtest/nasdaq_historical_data_june_2024.csv', index=True)