# Option Scanner for Undervalued Options

This project scans an options list to identify undervalued options using the Black-Scholes pricing model. It stores the results in a local MongoDB (or in production, AWS DynamoDB) for further analysis. The script is designed to be deployed as an AWS Lambda function.

## Features

- **Option Data Fetching:** Retrieves options data from DoltHub.
- **Black-Scholes Pricing:** Calculates theoretical call and put option prices.
- **Undervaluation Identification:** Compares market price with theoretical price to find undervalued options.
- **Database Storage:** Stores results in a database for quick retrieval and analysis.
- **AWS Lambda Ready:** Designed to be deployed serverlessly on AWS.

## Requirements

- **Python 3.8+**
- **Libraries:**
  - `numpy`
  - `scipy`
  - `requests`
  - `pymongo`
  - (Standard libraries: `json`, `datetime`, `logging`)

## Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/option-scanner.git
   cd option-scanner
