import yfinance as yf
import pandas as pd
import datetime

def check_earnings_and_ex_dividend(stock_symbol):
    # Get the stock information
    stock_data = yf.Ticker(stock_symbol)
    stock_info = stock_data.info

    # Extract earnings announcement date (if available)
    earnings_dates_exist = False
    if hasattr(stock_data, 'earnings_dates') and stock_data.earnings_dates is not None and len(stock_data.earnings_dates.get("Reported EPS").index.date) > 0:
        earnings_dates = stock_data.earnings_dates.get("Reported EPS").index.date
        earnings_dates_exist = True

    # Extract ex-dividend date (if available)
    ex_dividend_date = stock_info.get('exDividendDate')
    if ex_dividend_date:
        ex_dividend_date = pd.to_datetime(ex_dividend_date, unit='s')

    # Check if either event occurred in the past 14 days
    today = datetime.date.today()
    today_ts = pd.Timestamp.today()
    earnings_message = f"{stock_symbol} did not have an earnings announcement in the past 14 days."
    if earnings_dates_exist:
        # Loop through each date
        for earnings_date in earnings_dates:
            # Check if the date is within the past 14 days (inclusive)
            if earnings_date >= today - datetime.timedelta(days=14) and earnings_date <= today:
                earnings_message = f"{stock_symbol} had an earnings announcement on {earnings_date}."
                break

    if ex_dividend_date and ex_dividend_date >= today_ts - pd.Timedelta(days=14) and ex_dividend_date <= today_ts:
        ex_dividend_message = f"{stock_symbol} had an ex-dividend date on {ex_dividend_date}."
    else:
        ex_dividend_message = f"{stock_symbol} did not have an ex-dividend date in the past 14 days."

    return f"{earnings_message}\n{ex_dividend_message}"

# Example usage
stock_symbol = 'NVDA'  # Replace with your desired stock symbol
result = check_earnings_and_ex_dividend(stock_symbol)
print(result)
