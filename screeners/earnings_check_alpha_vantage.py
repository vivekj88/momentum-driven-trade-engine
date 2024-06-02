from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, timedelta

def check_earnings_last_14_days(ticker, api_key):
    ts = TimeSeries(key=api_key, output_format='json')
    data, meta_data = ts.get_company_overview(symbol=ticker)

    if 'EPS' in data:
        last_earnings_release = data['EPS']['latestEPSDate']

        try:
            latest_earnings_date = datetime.strptime(last_earnings_release, '%Y-%m-%d')
            if datetime.now() - timedelta(days=14) <= latest_earnings_date <= datetime.now():
                print(f"{ticker} announced earnings in the last 14 days.")
                return True
            else:
                print(f"{ticker} did not announce earnings in the last 14 days.")
                return False
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return False
    else:
        print("Earnings date information is not available.")
        return False

# Example usage
api_key = 'Y1UU25JQNJ3BD9HR'  # Replace with your Alpha Vantage API key
ticker = 'TGT'  # Example ticker
check_earnings_last_14_days(ticker, api_key)
