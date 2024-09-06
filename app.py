from flask import Flask, render_template, request, redirect, url_for
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Initialize Flask
app = Flask(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv('API_KEY')

# If no API_KEY in environment, request it from user (temporary)
if api_key is None:
    api_key = input("Introduce the API key: ")

# API headers
headers = {
    "API-Key": api_key
}

def arkham_request(url, params=None):
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error in API request: {response.status_code}"}

def arkham_hash(hash):
    url = f"https://api.arkhamintelligence.com/tx/{hash}"
    return arkham_request(url)

def arkham_transfers(start_time_str, usd_value):
    url = "https://api.arkhamintelligence.com/transfers"
    str_time_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
    start_time = int(str_time_dt.timestamp() * 1000)
    
    params = {
        "base": ["fixedfloat", "changenow", "simpleswap"],
        "flow": "out",
        "timeGte": start_time,
        "sortKey": "time",
        "sortDir": "asc",
        "usdLte": usd_value,
        "usdGte": usd_value * 0.95,
        "limit": 10
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error in API request: {response.status_code}"}

def print_out_tx(tx):
    result = []
    dict_keys = list(tx.keys())
    if 'transactionHash' in dict_keys:
        result.append(f"Blockchain: {tx['chain']}")
        result.append(f"Transaction Hash: {tx['transactionHash']}")
        result.append(f"From: {tx['fromAddress']['address']}")
        result.append(f"To: {tx['toAddress']['address']}")
        result.append(f"Token: {tx['tokenName']}")
        result.append(f"Amount: {tx['unitValue']} {tx['tokenSymbol']} = ${tx['historicalUSD']}")
        result.append(f"Date: {tx['blockTimestamp']}")
    elif 'txid' in dict_keys:  # BTC blockchain
        result.append(f"Blockchain: {tx['fromAddress']['chain']}")
        result.append(f"Transaction Hash: {tx['txid']}")
        result.append(f"From: {tx['fromAddress']['address']}")
        for address in tx['toAddresses']:
            result.append(f"To: {address['address']['address']}: {address['value']} BTC")
        result.append(f"Amount: {tx['unitValue']} BTC = ${tx['historicalUSD']}")
        result.append(f"Date: {tx['blockTimestamp']}")
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    hash = request.form.get('hash')
    hash_data = arkham_hash(hash)
    
    # Check if the hash was successful
    if "error" in hash_data:
        return render_template('error.html', error_message=hash_data["error"])
    
    start_time, usd_value = print_in_tx(hash_data)
    if start_time is None or usd_value is None:
        return render_template('error.html', error_message="Error with the input hash or blockchain not supported.")
    
    transfers_data = arkham_transfers(start_time, usd_value)
    if 'error' in transfers_data:
        return render_template('error.html', error_message=transfers_data['error'])

    transfers = transfers_data.get('transfers', [])
    return render_template('result.html', hash_data=hash_data, transfers=transfers)

def print_in_tx(hash_data):
    result = []
    blockchains_list = list(hash_data.keys())
    for blockchain in blockchains_list:
        if blockchain == 'bitcoin':
            result.append({
                "Blockchain": blockchain,
                "Transaction Hash": hash_data[blockchain]['txid'],
                "To": hash_data[blockchain]['outputs'][0]['address']['address'],
                "Amount": f"{hash_data[blockchain]['outputValue']} BTC = ${hash_data[blockchain]['outputUSD']}",
                "Date": hash_data[blockchain]['blockTimestamp']
            })
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['outputUSD']
        elif blockchain != 'tron':
            result.append({
                "Blockchain": blockchain,
                "Transaction Hash": hash_data[blockchain]['hash'],
                "From": hash_data[blockchain]['fromAddress'],
                "To": hash_data[blockchain]['toAddress'],
                "Amount": f"{hash_data[blockchain]['unitValue']} {hash_data[blockchain]['tokenSymbol']} = ${hash_data[blockchain]['usdValue']}",
                "Date": hash_data[blockchain]['blockTimestamp']
            })
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['usdValue']
    return None, None

if __name__ == '__main__':
    app.run(debug=True)