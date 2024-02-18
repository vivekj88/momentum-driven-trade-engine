import yfinance as yf
import datetime
import pandas as pd
import requests
import bs4
import matplotlib.pyplot as plt

# Get S&P 500 tickers from Wikipedia
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "lxml")
    table = soup.find("table", {"class": "wikitable sortable"})
    tickers = []
    for row in table.findAll("tr")[1:]:
        ticker = row.findAll("td")[0].text
        tickers.append(ticker.replace("\n", ""))
    return tickers

# Calculate the date range for the last 10 days
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=30)

# Download stock data
sp500_tickers = get_sp500_tickers()
data = yf.download(sp500_tickers, start=start_date, end=end_date)

# Filter out tickers with no price data
valid_tickers = []
for ticker in sp500_tickers:
    if ticker in data["Adj Close"]:
        valid_tickers.append(ticker)

# Initialize dictionaries to track highs and lows for each ticker
ticker_highs = {}
ticker_lows = {}

# Compare each day's price to previous and next day's price for each ticker
for ticker in valid_tickers:
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

# Check if each ticker has higher highs and higher lows
count_meeting_criteria = 0
for ticker in valid_tickers:
    if all(ticker_highs[ticker][i] > ticker_highs[ticker][i - 1] for i in range(1, len(ticker_highs[ticker]))) and \
            all(ticker_lows[ticker][i] > ticker_lows[ticker][i - 1] for i in range(1, len(ticker_lows[ticker]))):
        print(f"{ticker} meets the criteria.")
        data = yf.download(ticker, period="1mo", interval="1d")
        print(data)
        count_meeting_criteria += 1
print(f"Total tickers meeting the criteria: {count_meeting_criteria}")
