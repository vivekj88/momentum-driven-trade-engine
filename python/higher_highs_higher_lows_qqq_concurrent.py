from yahooquery import Ticker
import yfinance as yf
import datetime
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import warnings
from bs4 import BeautifulSoup

warnings.simplefilter(action='ignore', category=FutureWarning)

# Set options to show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

# Get Nasdaq 100 tickers from Wikipedia
def get_qqq_tickers():
    # URL of the Wikipedia page for Nasdaq-100
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"

    # Send an HTTP request to fetch the page content
    response = requests.get(url)

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the table containing the list of companies
    tables = soup.find_all("table", {"class": "wikitable sortable"})

    # Extract the tickers from the table
    tickers = []
    for row in tables[2].findAll("tr")[1:]:
        ticker = row.findAll("td")[1].text
        tickers.append(ticker.replace("\n", ""))
    tickers.append("QQQ")
    return tickers

def check_earnings_and_ex_dividend(stock_symbol):

    # Get the stock information
    stock_data = yf.Ticker(stock_symbol)
    stock_info = stock_data.info

    try:
        # Extract earnings announcement date (if available)
        earnings_dates_exist = False
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
        print(f"Exception in check_earnings_and_ex_dividend for {stock_symbol}: {e}")
        return None


# Calculate the date range for the last n days
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=14)

# Download stock data
tickers = get_qqq_tickers()
ticker_data = Ticker(tickers, asynchronous=True)
data = ticker_data.history(period='14d', interval='1d')
option_chain = ticker_data.option_chain
all_stocks_data = data


# Initialize dictionaries to track highs and lows for each ticker
ticker_highs = {}
ticker_lows = {}

# Compare each day's price to previous and next day's price for each ticker
for ticker in tickers:

    try:
        close_prices = data["adjclose"][ticker]
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
    

# Calculate daily returns for QQQ
daily_return = {}
daily_return["QQQ"] = data["adjclose"]["QQQ"].pct_change()

# Check if each ticker has higher highs and higher lows
count_meeting_criteria = 0
tickers_meeting_criteria = {}
for ticker in tickers:
    # Calculate daily returns for stocks

    try:
        daily_return[ticker] = all_stocks_data["adjclose"][ticker].pct_change()
        if len(ticker_highs[ticker]) > 1 and len(ticker_lows[ticker]) > 1 and \
            all(ticker_highs[ticker][i] > ticker_highs[ticker][i - 1] for i in range(1, len(ticker_highs[ticker]))) and \
                all(ticker_lows[ticker][i] > ticker_lows[ticker][i - 1] for i in range(1, len(ticker_lows[ticker]))) and \
                    daily_return[ticker].mean() > daily_return["QQQ"].mean():
            tickers_meeting_criteria[ticker] = daily_return[ticker].mean()
            count_meeting_criteria += 1

    except Exception as e:
        print(f"Ticker {ticker} threw exception {e}")

# Remove tickers that are not optionable
for ticker in tickers_meeting_criteria:
    try:
        if isinstance(option_chain, str) or option_chain.empty:
            tickers_meeting_criteria.remove(ticker) 
    except Exception as e:
        print(f"error while checking if {ticker} is optionable {e}")

# Filter out tickers with no price data and no special events
with ThreadPoolExecutor() as executor:
    valid_tickers = list(executor.map(check_earnings_and_ex_dividend, tickers_meeting_criteria))
      
# Convert valid_tickers to a set for efficient membership testing
valid_tickers_set = set(valid_tickers)

# Remove entries from tickers_meeting_criteria using list comprehension
tickers_meeting_criteria_filtered = {ticker: value for ticker, value in tickers_meeting_criteria.items() 
                             if ticker in valid_tickers_set}

# Count the number of removed elements (length of original dictionary minus current length)
num_removed = len(set(tickers_meeting_criteria.keys())) - len(set(tickers_meeting_criteria_filtered.keys()))

count_meeting_criteria -= num_removed    

print(f"Total tickers meeting the criteria: {count_meeting_criteria}")
print(f"QQQ Daily Return: {daily_return['QQQ'].mean()}")      

# Sort the dictionary by value in descending order
sorted_data = dict(sorted(tickers_meeting_criteria_filtered.items(), key=lambda item: item[1], reverse=True))

# Create a DataFrame from the sorted dictionary
# df = pd.DataFrame.from_dict(sorted_data, orient='index', columns=['value'])
df = pd.DataFrame.from_dict(sorted_data, orient='index', columns=['daily_return'])

# Reset index
df = df.reset_index()

# Rename the index column
df = df.rename(columns={'index': 'ticker'})

df['relative_strength'] = (df['daily_return'] - daily_return['QQQ'].mean()) * 100 / daily_return['QQQ'].mean()

# Print the DataFrame
print(df)