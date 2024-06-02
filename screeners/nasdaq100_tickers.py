import requests
from bs4 import BeautifulSoup

def get_nasdaq_tickers(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', {'class': 'wikitable sortable'})
    tickers = []

    for row in table.findAll('tr')[1:]:
        ticker = row.findAll('td')[0].text.strip()
        tickers.append(ticker)

    return tickers

url = "https://en.wikipedia.org/wiki/Nasdaq-100"
tickers = get_nasdaq_tickers(url)
print(tickers)
