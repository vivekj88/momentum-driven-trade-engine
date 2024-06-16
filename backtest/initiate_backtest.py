import datetime
import subprocess
import pandas_market_calendars as mcal

# Define the program to call
program_to_call = "backtest/higher_highs_higher_lows_nasdaq.py"

# Define the start and end dates
start_date = datetime.datetime.strptime("2024-04-01", "%Y-%m-%d").date()
end_date = datetime.date.today()

# Get the NYSE calendar
nyse = mcal.get_calendar('NYSE')

# Get market open dates between start_date and end_date
market_days = nyse.valid_days(start_date=start_date, end_date=end_date)

# Convert market_days to a list of strings
market_days_str = market_days.strftime('%Y-%m-%d').tolist()

# Loop through market open dates
for market_day in market_days_str:
    print(f"Processing date: {market_day}")

    # Call the program with the date string as an argument
    try:
        subprocess.run(["python", program_to_call, market_day])
    except Exception as e:
        print(f"An error occurred while running the subprocess: {e}")