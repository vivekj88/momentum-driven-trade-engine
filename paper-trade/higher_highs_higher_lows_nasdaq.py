import requests
from yahooquery import Ticker
import yfinance as yf
import datetime
import pandas as pd
import warnings
import os
from concurrent.futures import ThreadPoolExecutor
import uuid

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

import pandas as pd

import datetime


def upsert_screener_log(df, daily_return_comp, all_stocks_data):
  """
  This function processes a DataFrame by calculating relative strength, setting last price, and adding a date column.

  Args:
      df (pandas.DataFrame): The DataFrame to process.
      daily_return_comp (pandas.Series): The daily return data for the comparison group.
      all_stocks_data (pandas.DataFrame): DataFrame containing stock data (assumed to have 'adjclose' column).

  Returns:
      pandas.DataFrame: The processed DataFrame.
  """
  # Create a copy of the DataFrame (avoid modifying original data)
  screener_log = df.copy()

  # Calculate relative strength
  screener_log['relative_strength'] = (screener_log['daily_return'] - daily_return_comp.mean()) * 100

  # Multiply daily return by 100
  screener_log['daily_return'] = screener_log['daily_return'] * 100

  # Set last price (assuming 'ticker' column exists in df and 'adjclose' in all_stocks_data)
  for i, row in screener_log.iterrows():
    screener_log.loc[i, 'last_price'] = all_stocks_data["adjclose"][row['ticker']].iloc[-1]

  # Set date
  screener_log['date'] = datetime.date.today().isoformat()

  return screener_log

import datetime

def process_trades_upsert_trade_log(df, TRADE_LOG_PATH, all_stocks_data):
  """
  This function creates a trade log DataFrame from an input DataFrame.

  Args:
      df (pandas.DataFrame): The DataFrame containing stock data.

  Returns:
      pandas.DataFrame: The trade log DataFrame with additional columns.
  """

  INVESTMENT_AMOUNT = 100
  # Read existing data (assuming the file exists)
  try:
    trade_log = pd.read_csv(TRADE_LOG_PATH)

  except FileNotFoundError:
    # Handle case where existing file doesn't exist
    print(f"File {TRADE_LOG_PATH} not found. Creating a new CSV with today's trades if eligible.")
    trade_log = pd.DataFrame(columns=['trade_id', 'ticker', 'daily_return_open', 'relative_strength_open', 'open_price', 'open_date', 'open_timestamp', 'stocks_bought', 'cost_price', 'close_price', 'close_date', 'close_timestamp', 'stocks_sold', 'selling_price', 'profit', 'profit_percent'])

  tickers_screener = set(df['ticker'])    
  tickers_tradelog = set()

  if not trade_log.empty:
    trade_log_open_only = trade_log.copy()
    print("trade_log_open_only before")
    print(trade_log_open_only)
    trade_log_open_only = trade_log_open_only.drop(trade_log_open_only.index[~trade_log_open_only['close_price'].isnull()])
    tickers_tradelog = set(trade_log_open_only['ticker'])
    print("trade_log_open_only")
    print(trade_log_open_only)
    print("tickers_tradelog")
    print(tickers_tradelog)

  # Find tickers present in screener but not in trade log. These will be used for new opening trades.
  tickers_to_open = tickers_screener - tickers_tradelog

  print("tickers_to_open")
  print(tickers_to_open)
  
  for ticker in tickers_to_open:
      trade_id = uuid.uuid4()
      daily_return_open = df[df['ticker'] == ticker]['daily_return'].values[0]
      relative_strength_open = df[df['ticker'] == ticker]['relative_strength'].values[0]
    
      open_price = df[df['ticker'] == ticker]['last_price'].values[0]
      open_date = df[df['ticker'] == ticker]['date'].values[0]
      open_timestamp = datetime.datetime.now()
      stocks_bought = INVESTMENT_AMOUNT / open_price
      cost_price = INVESTMENT_AMOUNT

      close_price = None
      close_date = None
      close_timestamp = None
      stocks_sold = None
      selling_price = None
      profit = None
      profit_percent = None

      new_row = {'trade_id': trade_id, 'ticker': ticker, 'daily_return_open': daily_return_open, 'relative_strength_open': relative_strength_open, 
                  'open_price': open_price, 'open_date': open_date, 'open_timestamp': open_timestamp, 'stocks_bought': stocks_bought, 'cost_price': cost_price, 
                  'close_price': close_price, 'close_date': close_date, 'close_timestamp': close_timestamp, 'stocks_sold': stocks_sold, 'selling_price': selling_price, 
                  'profit': profit, 'profit_percent': profit_percent }
      trade_log = pd.concat([trade_log, pd.DataFrame([new_row])], ignore_index=True)

  # Find tickers present in trade log but not in screener. These will be used to close out the trades.
  tickers_to_close = tickers_tradelog - tickers_screener

  for ticker in tickers_to_close:
      trade_id = trade_log[trade_log['ticker'] == ticker]['trade_id'].values[0]
      daily_return_open = trade_log[trade_log['ticker'] == ticker]['daily_return_open'].values[0]
      relative_strength_open = trade_log[trade_log['ticker'] == ticker]['relative_strength_open'].values[0]
    
      open_price = trade_log[trade_log['ticker'] == ticker]['open_price'].values[0]
      open_date = trade_log[trade_log['ticker'] == ticker]['open_date'].values[0]
      open_timestamp = trade_log[trade_log['ticker'] == ticker]['open_timestamp'].values[0]
      stocks_bought = trade_log[trade_log['ticker'] == ticker]['stocks_bought'].values[0]
      cost_price = trade_log[trade_log['ticker'] == ticker]['cost_price'].values[0]

      close_price = all_stocks_data["adjclose"][ticker].iloc[0]
      close_date = datetime.datetime.now().strftime('%Y-%m-%d')
      close_timestamp = datetime.datetime.now()
      stocks_sold = stocks_bought
      selling_price = stocks_sold * close_price
      profit = selling_price - cost_price
      profit_percent = profit * 100 / cost_price

      update_row = {'trade_id': trade_id, 'ticker': ticker, 'daily_return_open': daily_return_open, 'relative_strength_open': relative_strength_open, 
                  'open_price': open_price, 'open_date': open_date, 'open_timestamp': open_timestamp, 'stocks_bought': stocks_bought, 'cost_price': cost_price, 
                  'close_price': close_price, 'close_date': close_date, 'close_timestamp': close_timestamp, 'stocks_sold': stocks_sold, 'selling_price': selling_price, 
                  'profit': profit, 'profit_percent': profit_percent }
      
      trade_log.loc[trade_log['trade_id'] == update_row['trade_id'], update_row.keys()] = update_row.values()


  return trade_log

def append_dataframe_deduped(existing_file, df_to_append, identifier_cols):
  """
  This function appends a DataFrame to an existing CSV file after deduplication.

  Args:
      existing_file (str): The path to the existing CSV file.
      df_to_append (pandas.DataFrame): The DataFrame to append.
      identifier_cols (list): A list of column names for duplicate checking.

  Returns:
      None
  """

  # Read existing data (assuming the file exists)
  try:
    existing_df = pd.read_csv(existing_file)
  except FileNotFoundError:
    # Handle case where existing file doesn't exist
    print(f"File {existing_file} not found. Creating a new CSV with the provided data.")
    existing_df = df_to_append.copy()

  # Append the new DataFrame and drop duplicates
  appended_df = pd.concat([df_to_append,existing_df], ignore_index=True)
  appended_df.drop_duplicates(subset=identifier_cols, inplace=True)

  # Write the deduplicated DataFrame to the CSV file
  appended_df.to_csv(existing_file, index=False)

  print(f"Data deduplicated and appended to {existing_file} successfully!")


TRADE_LOG_PATH = "trade_log.csv"
# Calculate the date range for the last n days
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=14)

# Download stock data
tickers = get_nasdaq_tickers()
# tickers = ['COMP','ACDC','PRME','AAPL','PLCE','RENT', 'SITM', 'TNDM', 'ADMA', 'NVCR', 'TMDX', 'JYNT', 'ATNI']
print(tickers)
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
# df = df.drop(df.index[df['ticker'] == 'INTR'])

# Create screener log and append to csv
screener_log = upsert_screener_log(df, daily_return['COMP'], all_stocks_data)
append_dataframe_deduped("hhhl.csv", screener_log, ['ticker','date'])

# Create trade log and append to csv
trade_log = process_trades_upsert_trade_log(screener_log, TRADE_LOG_PATH, all_stocks_data)
append_dataframe_deduped("trade_log.csv", trade_log, ['ticker','open_timestamp'])

print(trade_log)