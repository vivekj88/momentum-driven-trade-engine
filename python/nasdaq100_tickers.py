import requests
from bs4 import BeautifulSoup

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

# Print the list of tickers
print("Nasdaq-100 Tickers:")
for ticker in tickers:
    print(ticker)
