import yfinance as yf
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import warnings
from concurrent.futures import ThreadPoolExecutor

warnings.simplefilter(action='ignore', category=FutureWarning)

# Set options to show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

# Get tickers
def get_nasdaq_tickers():
    filename = 'nyse.csv'

    tickers=[]
    with open(filename, "r") as csvfile:
        # Skip the header line (assuming the first line contains headers)
        next(csvfile)  # Skip the first line

        for line in csvfile:
        # Extract the first element (assuming it's the ticker symbol)
            tickers.append(line.strip().split(",")[0])
    tickers.append("^NYA")
    return tickers

def check_earnings_and_ex_dividend(stock_symbol):

    # Get the stock information
    stock_data = yf.Ticker(stock_symbol)
    stock_info = stock_data.info

    try:

        # Extract earnings announcement date (if available)
        earnings_dates_exist = False
        print(f"stock_data: {stock_data}")
        if hasattr(stock_data, 'earnings_dates') and stock_data.earnings_dates is not None and len(stock_data.earnings_dates.get("Reported EPS").index.date) > 0:
            earnings_dates = stock_data.earnings_dates.get("Reported EPS").index.date
            earnings_dates_exist = True

        # Extract ex-dividend date (if available)
        ex_dividend_date = stock_info.get('exDividendDate')
        if ex_dividend_date:
            ex_dividend_date = pd.to_datetime(ex_dividend_date, unit='s')

        # Check for earnings announcements and ex-dividend dates
        has_events = False
        today = datetime.date.today()
        today_ts = pd.Timestamp.today()

        if earnings_dates_exist:
            # Loop through each date
            for earnings_date in earnings_dates:
                if earnings_date >= today - datetime.timedelta(days=14) and earnings_date <= today:
                    has_events = True
                    break

        if ex_dividend_date and ex_dividend_date >= today_ts - pd.Timedelta(days=14) and ex_dividend_date <= today_ts:
            has_events = True

        if has_events:
            print(f"{stock_symbol} has events")
            return None
        else:
            print(f"{stock_symbol} has no events")
            return stock_symbol
    
    except Exception as e:
        print(f"Exception in check_earnings_and_ex_dividend for {stock_symbol} ----> {e}")
        return None

# Calculate the date range for the last n days
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=14)

# Download stock data
tickers = get_nasdaq_tickers()
data = yf.download(tickers, start=start_date, end=end_date)
all_stocks_data = data

# Filter out tickers with no price data and no special events
with ThreadPoolExecutor(max_workers=1) as executor:
    valid_tickers = list(executor.map(check_earnings_and_ex_dividend, tickers))
    print(f"valid_tickers: {valid_tickers}")

# Initialize dictionaries to track highs and lows for each ticker
ticker_highs = {}
ticker_lows = {}

# Compare each day's price to previous and next day's price for each ticker
for ticker in valid_tickers:
    print(f"{ticker} in valid_tickers")
    if ticker is not None:
        try:
            close_prices = data["Adj Close"][ticker]
            highs = []
            lows = []
            for i in range(1, len(close_prices) - 1):
                if close_prices.iloc[i] > close_prices.iloc[i - 1] and close_prices.iloc[i] > close_prices.iloc[i + 1]:
                    highs.append(close_prices.iloc[i])
                elif close_prices.iloc[i] < close_prices.iloc[i - 1] and close_prices.iloc[i] < close_prices.iloc[i + 1]:
                    lows.append(close_prices.iloc[i])
            ticker_highs[ticker] = highs
            ticker_lows[ticker] = lows
        except Exception as e:
                print(f"{ticker} threw an exception")

# Calculate daily returns for ^NYA
daily_return = {}
daily_return["^NYA"] = data["Adj Close"]["^NYA"].pct_change()

# Check if each ticker has higher highs and higher lows
count_meeting_criteria = 0
tickers_meeting_criteria = {}
for ticker in valid_tickers:
    if ticker is not None:
        try:
            # Calculate daily returns for stocks
            daily_return[ticker] = all_stocks_data["Adj Close"][ticker].pct_change()
            if len(ticker_highs[ticker]) > 1 and len(ticker_lows[ticker]) > 1 and \
                all(ticker_highs[ticker][i] > ticker_highs[ticker][i - 1] for i in range(1, len(ticker_highs[ticker]))) and \
                    all(ticker_lows[ticker][i] > ticker_lows[ticker][i - 1] for i in range(1, len(ticker_lows[ticker]))) and \
                        daily_return[ticker].mean() > daily_return["^NYA"].mean():
                tickers_meeting_criteria[ticker] = daily_return[ticker].mean()
                count_meeting_criteria += 1
        except Exception as e:
            print(f"{ticker} threw an exception")
print(f"Total tickers meeting the criteria: {count_meeting_criteria}")
print(f"^NYA Daily Return: {daily_return['^NYA'].mean()}")      

# Sort the dictionary by value in descending order
sorted_data = dict(sorted(tickers_meeting_criteria.items(), key=lambda item: item[1], reverse=True))

# Create a DataFrame from the sorted dictionary
df = pd.DataFrame.from_dict(sorted_data, orient='index', columns=['value'])

# Print the DataFrame
print(df)
