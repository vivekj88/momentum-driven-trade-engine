import requests
from yahooquery import Ticker
import yfinance as yf
import datetime
import pandas as pd
import warnings
from concurrent.futures import ThreadPoolExecutor

warnings.simplefilter(action='ignore', category=FutureWarning)

# Set options to show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

# Get tickers
def get_nasdaq_tickers():
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

def fetch_earnings(from_date, to_date):
  """
  This function calls the stocktwits API to pull earnings between the specified from_date and to_date.
[]
  Args:
      from_date: The starting date in YYYY-MM-DD format.
      to_date: The ending date in YYYY-MM-DD format.
  """

  # Base URL for the stocktwits earnings API endpoint
  base_url = "http://api.stocktwits.com/api/2/discover/earnings_calendar"

  # Construct the query parameters
  params = {
    "date_from": from_date,
    "date_to": to_date,
  }

  try:
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    }

    # Send a GET request to the API
    response = requests.get(base_url, params=params, headers=headers)
    response.raise_for_status()  # Raise an exception for non-200 status codes

    # Parse the JSON response
    return response.json()

  except requests.exceptions.RequestException as e:
    print(f"An error occurred while making the API request: {e}")

def check_ex_dividend(stock_symbol):

    # Get the stock information
    stock_data = yf.Ticker(stock_symbol)
    stock_info = stock_data.info

    try:

        # Extract ex-dividend date (if available)
        ex_dividend_date = stock_info.get('exDividendDate')
        if ex_dividend_date:
            ex_dividend_date = pd.to_datetime(ex_dividend_date, unit='s')

        # Check for ex-dividend dates
        ex_dividend_occurred = False
        today = datetime.date.today()
        today_ts = pd.Timestamp.today()

        if ex_dividend_date and ex_dividend_date >= today_ts - pd.Timedelta(days=14) and ex_dividend_date <= today_ts:
            ex_dividend_occurred = True

        if ex_dividend_occurred:
            print(f"Ex-dividend occurred, skipping ticker: {stock_symbol}")
            return None
        else:
            return stock_symbol

    except Exception as e:
        print(f"Exception in check_ex_dividend for {stock_symbol}: {e}")
        return None


# Calculate the date range for the last n days
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=14)

# Download stock data
tickers = get_nasdaq_tickers()
ticker_data = Ticker(tickers, asynchronous=True)
data = ticker_data.history(period='14d', interval='1d')
# print(data)
option_chain = ticker_data.option_chain
all_stocks_data = data

# Fetch earnings
earnings_calendar = fetch_earnings(start_date.date(), end_date.date())

for ticker in tickers:
    # Iterate over each day's earnings data
    for date, earnings_data in earnings_calendar["earnings"].items():
        # Iterate over each stock in the current day's earnings
        for stock in earnings_data["stocks"]:
            if stock["symbol"] == ticker and ticker in tickers:
                print(f"Earnings event occurred, skipping ticker: {ticker}")
                tickers.remove(ticker)


# Initialize dictionaries to track highs and lows for each ticker
ticker_highs = {}
ticker_lows = {}

# Compare each day's price to previous and next day's price for each ticker
for ticker in tickers:

    try:
        close_prices = data["low"][ticker]
        # print("close_prices")
        # print(close_prices)
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
        print(f"Ticker {ticker} threw exception {e}")
    

# Calculate daily returns for COMP
daily_return = {}
daily_return["COMP"] = data["low"]["COMP"].pct_change()

# Check if each ticker has higher highs and higher lows
count_meeting_criteria = 0
tickers_meeting_criteria = {}
for ticker in tickers:
    # Calculate daily returns for stocks

    try:
        daily_return[ticker] = all_stocks_data["low"][ticker].pct_change()
        # print(f"daily return of {ticker}: {daily_return[ticker]}")
        # print(f"price of {ticker}: {all_stocks_data['low'][ticker]}")
        # Remove cheaper stocks
        if len(ticker_highs[ticker]) > 1 and len(ticker_lows[ticker]) > 1 and \
            all(ticker_highs[ticker][i] > ticker_highs[ticker][i - 1] for i in range(1, len(ticker_highs[ticker]))) and \
                all(ticker_lows[ticker][i] > ticker_lows[ticker][i - 1] for i in range(1, len(ticker_lows[ticker]))) and \
                    daily_return[ticker].mean() > daily_return["COMP"].mean() and \
                    all_stocks_data["low"][ticker].iloc[0] > 5:
            tickers_meeting_criteria[ticker] = daily_return[ticker].mean()
            count_meeting_criteria += 1

    except Exception as e:
        print(f"Ticker {ticker} threw exception {e}")

# Remove tickers that are not optionable
tickers_meeting_criteria_optionable = tickers_meeting_criteria.copy()
for ticker in tickers_meeting_criteria:
    try:
        if isinstance(option_chain, pd.DataFrame) and not option_chain.empty:
            try:
                a = option_chain.loc[ticker]
            except:
                del tickers_meeting_criteria_optionable[ticker] 
                print(f"Removing non-optionable ticker {ticker}")
        else:
            del tickers_meeting_criteria_optionable[ticker]
            print(f"Removing non-optionable ticker {ticker}")
    except Exception as e:
        print(f"error while checking if {ticker} is optionable {e}")

# Filter out tickers with no price data and no special events
with ThreadPoolExecutor() as executor:
    valid_tickers = list(executor.map(check_ex_dividend, tickers_meeting_criteria))
      
# Convert valid_tickers to a set for efficient membership testing
valid_tickers_set = set(valid_tickers)

# Remove entries from tickers_meeting_criteria using list comprehension
tickers_meeting_criteria_filtered = {ticker: value for ticker, value in tickers_meeting_criteria_optionable.items() 
                             if ticker in valid_tickers_set}

# Count the number of removed elements (length of original dictionary minus current length)
num_removed = len(set(tickers_meeting_criteria_optionable.keys())) - len(set(tickers_meeting_criteria_filtered.keys()))

count_meeting_criteria -= num_removed    

print(f"Total tickers meeting the criteria: {count_meeting_criteria}")
print(f"COMP Daily Return: {daily_return['COMP'].mean() * 100}")      

# Sort the dictionary by value in descending order
sorted_data = dict(sorted(tickers_meeting_criteria_filtered.items(), key=lambda item: item[1], reverse=True))

# Create a DataFrame from the sorted dictionary
df = pd.DataFrame.from_dict(sorted_data, orient='index', columns=['daily_return'])

# Reset index
df = df.reset_index()

# Rename the index column
df = df.rename(columns={'index': 'ticker'})

df['relative_strength'] = (df['daily_return'] - daily_return['COMP'].mean()) * 100
df['daily_return'] = df['daily_return'] * 100

# Print the DataFrame
print(df)