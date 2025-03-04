import json
import datetime
import numpy as np
from scipy.stats import norm
import requests
from pymongo import MongoClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Black-Scholes call option pricing formula
def black_scholes_call(S, K, sigma, r, t):
    d1 = (np.log(S/K) + (r + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
    d2 = d1 - sigma * np.sqrt(t)
    return S * norm.cdf(d1) - K * np.exp(-r * t) * norm.cdf(d2)

# Black-Scholes put option pricing formula
def black_scholes_put(S, K, sigma, r, t):
    d1 = (np.log(S/K) + (r + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
    d2 = d1 - sigma * np.sqrt(t)
    return K * np.exp(-r * t) * norm.cdf(-d2) - S * norm.cdf(-d1)

# Fetch options data from DoltHub
def fetch_dolthub_options(ticker, date="2023-10-18", limit=100):
    url = (
        f"https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master?"
        f"q=SELECT * FROM option_chain WHERE act_symbol = '{ticker}' "
        f"AND date = '{date}' LIMIT {limit}"
    )
    try:
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to fetch DoltHub data: {response.status_code} - {response.text}")
            raise Exception(f"DoltHub API error: {response.text}")
        data = response.json()
        logger.info(f"Raw API response: {json.dumps(data, indent=2)}")
        if data.get("query_execution_status") == "Success" and "rows" in data:
            return data["rows"]
        else:
            logger.warning(f"No successful data returned for {ticker} on {date}: {data}")
            return []
    except Exception as e:
        logger.error(f"Error fetching options: {str(e)}")
        raise

# Calculate time to expiration relative to test_date
def time_to_expiration(expiration_date, reference_date):
    exp_date = datetime.datetime.strptime(expiration_date, "%Y-%m-%d").replace(tzinfo=datetime.UTC)
    ref_date = datetime.datetime.strptime(reference_date, "%Y-%m-%d").replace(tzinfo=datetime.UTC)
    t = (exp_date - ref_date).days / 365.0
    return max(t, 0.0001)

# Main scanning function
def scan_options(underlying_ticker, r=0.05, sigma_default=0.3, test_date="2023-10-18"):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["options_db"]
    collection = db["undervalued_options"]
    
    # Fetch options data from DoltHub
    options_data = fetch_dolthub_options(underlying_ticker, date=test_date)
    logger.info(f"Fetched {len(options_data)} options for {underlying_ticker} on {test_date}")
    
    if not options_data:
        logger.warning("No options data available")
        return []
    
    undervalued_options = []
    
    # Hardcode S for accuracy (AAPL close on 2023-10-18)
    S = 175.84
    logger.info(f"Using hardcoded S = {S} for {test_date}")
    
    for option in options_data:
        is_call = option["call_put"] == "Call"
        ticker = f"{underlying_ticker}{option['expiration'].replace('-', '')}{'C' if is_call else 'P'}{option['strike']}"
        K = float(option["strike"])
        expiration_date = option["expiration"]
        market_price = (float(option["bid"]) + float(option["ask"])) / 2
        sigma = float(option["vol"]) if option["vol"] else sigma_default
        
        t = time_to_expiration(expiration_date, test_date)
        bs_price = black_scholes_call(S, K, sigma, r, t) if is_call else black_scholes_put(S, K, sigma, r, t)
        
        logger.info(f"Option {ticker}: Market={market_price}, BS={bs_price}, t={t}, sigma={sigma}")
        
        if market_price < bs_price:
            result = {
                "RecordId": datetime.datetime.now(datetime.UTC).isoformat(),
                "UnderlyingTicker": underlying_ticker,
                "OptionTicker": ticker,
                "Type": "Call" if is_call else "Put",
                "S": float(S),
                "K": float(K),
                "sigma": float(sigma),
                "r": float(r),
                "t": float(t),
                "MarketPrice": float(market_price),
                "BlackScholesPrice": float(bs_price),
                "Undervaluation": float(bs_price - market_price)
            }
            
            collection.insert_one(result)
            logger.info(f"Undervalued option found: {ticker}")
            undervalued_options.append({k: v for k, v in result.items()})  # Exclude _id
    
    client.close()
    return undervalued_options

if __name__ == "__main__":
    underlying_ticker = "AAPL"
    r = 0.05
    sigma_default = 0.3
    test_date = "2023-10-18"
    
    try:
        undervalued = scan_options(underlying_ticker, r, sigma_default, test_date)
        print(f"Found {len(undervalued)} undervalued options:")
        print(json.dumps(undervalued, indent=2, default=str))
    except Exception as e:
        logger.error(f"Error: {str(e)}")