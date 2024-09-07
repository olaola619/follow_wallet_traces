from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime

# Initialize Flask
app = Flask(__name__)

def arkham_request(url, headers, params=None):
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error in API request: {response.status_code}"}

def arkham_hash(hash, headers):
    url = f"https://api.arkhamintelligence.com/tx/{hash}"
    return arkham_request(url, headers)

def arkham_transfers(headers, start_time_str, usd_value):
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

@app.route('/', methods=['GET', 'POST'])
def index():
    
    # Find "to" wallet
    hash_data = None
    transfers = None
    error_message = None

    if request.method == 'POST' and 'hash' in request.form:
        # API headers
        api_key = request.form.get('api_key')
        headers = {
            "API-Key": api_key
        }

        # Single Hash
        hash = request.form.get('hash')
        hash_data = arkham_hash(hash, headers)
        
        # Check if the hash was successful
        if "error" in hash_data:
            error_message = hash_data["error"]
        else:
            start_time, usd_value = print_in_tx(hash_data)
            if start_time is None or usd_value is None:
                error_message = "Error with the input hash or blockchain not supported."
            else:
                transfers_data = arkham_transfers(headers, start_time, usd_value)
                if 'error' in transfers_data:
                    error_message = transfers_data['error']
                else:
                    transfers = transfers_data.get('transfers', [])

    # Find most common addresses
    address_list = []
    hash_data_multiple = None
    transfers_multiple = None

    if request.method == 'POST' and 'hashes' in request.form:
        # API headers
        api_key = request.form.get('api_key')
        headers = {
            "API-Key": api_key
        }

        # Multiple Hashes
        hashes_input = request.form.get('hashes')
        hashes = hashes_input.splitlines()
        hashes = list(set(hashes))  # Eliminate duplicates
        multi_hash_data = []

        for hash in hashes:
            hash = hash.strip()
            if not hash:
                continue

            # Process each hash
            hash_data_multiple = arkham_hash(hash, headers)

            if "error" in hash_data_multiple:
                error_message = hash_data_multiple["error"]
            else:
                start_time, usd_value = print_in_tx_multiple(hash_data_multiple)

                if start_time is None or usd_value is None:
                    error_message = "Error with the input hash or blockchain not supported."
                else:
                    transfers_data = arkham_transfers(headers, start_time, usd_value)
                    if 'error' in transfers_data:
                        error_message = transfers_data['error']
                    else:
                        transfers_multiple = transfers_data.get('transfers', [])

                        for transfer in transfers_multiple:
                            dict_keys = (list(transfer.keys()))
                            if 'transactionHash' in dict_keys:
                                multi_hash_data.append({
                                    "blockchain": transfer['chain'],
                                    "hash": transfer['transactionHash'],
                                    "to": transfer['toAddress']['address'],
                                })
                            elif 'txid' in dict_keys: # BTC blockchain
                                for address in transfer['toAddresses']:
                                    multi_hash_data.append({
                                        "blockchain": transfer['fromAddress']['chain'],
                                        "hash": transfer['txid'],
                                        "to": address['address']['address'],
                                    })
        
        count_reps = {}
        for element in multi_hash_data:
            to_address = element["to"]
            if to_address in count_reps:
                count_reps[to_address] += 1
            else:
                count_reps[to_address] = 1
                
        
        agregated_addresses = set()
        for hash in multi_hash_data:
            to_address = hash['to']
            if to_address not in agregated_addresses:
                new_element = {k: hash[k] for k in ("blockchain", "to")}
                new_element["repetitions"] = count_reps[to_address]

                address_list.append(new_element)
                agregated_addresses.add(to_address)

        address_list.sort(key = lambda x: x["repetitions"], reverse = True)

    return render_template('index.html', hash_data=hash_data, transfers=transfers, address_list=address_list, error_message=error_message)

def print_in_tx(hash_data):
    blockchains_list = list(hash_data.keys())
    for blockchain in blockchains_list:
        if blockchain == 'bitcoin':
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['outputUSD']
        elif blockchain != 'tron':
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['usdValue']
    return None, None

def print_in_tx_multiple(hash_data):
    blockchains_list = list(hash_data.keys())
    for blockchain in blockchains_list:
        if blockchain == 'bitcoin':
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['outputUSD']
        elif blockchain != 'tron':
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['usdValue']
    return None, None

if __name__ == '__main__':
    app.run(debug=True)