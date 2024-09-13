from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime, timedelta

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

def arkham_transfer_hash(hash, chain, transferType, headers):
    url = f"https://api.arkhamintelligence.com/transfers/tx/{hash}"

    params = {
        "chain": chain,
        "transferType": transferType,
    }

    response = arkham_request(url, headers=headers, params=params)
    return response

def arkham_transfers(headers, start_time_str, usd_value):
    url = "https://api.arkhamintelligence.com/transfers"
    str_time_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
    # str_time_dt += timedelta(minutes = 1)
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
    hash_data = []
    transfers = []
    error_message = None

    if request.method == 'POST' and 'hash' in request.form:
        # API headers
        api_key = request.form.get('api_key')
        headers = {
            "API-Key": api_key
        }

        # Single Hash
        hash = request.form.get('hash')
        hash_data_pre = arkham_hash(hash, headers)

        for blockchain, data in hash_data_pre.items():
            if blockchain == 'bitcoin':
                hash_data.append({
                    "chain": 'bitcoin',
                    "transactionHash":  data["txid"],
                    "fromAddress": {"address": data["inputs"][0]["address"]["address"]},
                    "toAddress": {"address": data["outputs"][0]["address"]["address"]},
                    "unitValue": data["inputValue"],
                    "tokenSymbol": 'BTC',
                    "blockTimestamp": data["blockTimestamp"],
                    "historicalUSD": data["inputUSD"],
                })
            else:
                hash_data = arkham_transfer_hash(hash, blockchain, 'token' if data['usdValue'] == 0 else 'external', headers)
        
        # Check if the hash was successful
        if "error" in hash_data:
            error_message = hash_data["error"]
        else:
            # start_time, usd_value = print_in_tx(hash_data)
            start_time = hash_data[0]["blockTimestamp"]
            usd_value = hash_data[0]["historicalUSD"]
            if start_time is None or usd_value is None:
                error_message = "Error with the input hash or blockchain not supported."
            else:
                transfers_data = arkham_transfers(headers, start_time, usd_value)
                if 'error' in transfers_data:
                    error_message = transfers_data['error']
                else:
                    transfers_pre = transfers_data.get('transfers', [])
                    for transfer in transfers_pre:
                        original_hash_timestamp_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                        original_hash_timestamp = int(original_hash_timestamp_dt.timestamp() * 1000)
                        transfer_timestamp_dt = datetime.strptime(transfer["blockTimestamp"], "%Y-%m-%dT%H:%M:%SZ")
                        transfer_timestamp = int(transfer_timestamp_dt.timestamp() * 1000)
                        if transfer_timestamp > original_hash_timestamp:
                            transfers.append(transfer)

    # Find most common addresses
    address_list = []
    transfers_multiple = []
    hashes_data = []

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
            # hash_data_multiple = arkham_hash(hash, headers)
            # Process each hash
            hash_data_multiple = []
            hash_data_multiple_pre = arkham_hash(hash, headers)
            for blockchain, data in hash_data_multiple_pre.items():
                if blockchain == 'bitcoin':
                    hash_data_multiple.append({
                        "chain": 'bitcoin',
                        "transactionHash":  data["txid"],
                        "fromAddress": {"address": data["inputs"][0]["address"]["address"]},
                        "toAddress": {"address": data["outputs"][0]["address"]["address"]},
                        "unitValue": data["inputValue"],
                        "tokenSymbol": 'BTC',
                        "blockTimestamp": data["blockTimestamp"],
                        "historicalUSD": data["inputUSD"],
                    })
                else:
                    hash_data_multiple = arkham_transfer_hash(hash, blockchain, 'token' if data['usdValue'] == 0 else 'external', headers)


            hashes_data.append(hash_data_multiple)

            if "error" in hash_data_multiple:
                error_message = hash_data_multiple["error"]
            else:
                # start_time, usd_value = print_in_tx_multiple(hash_data_multiple)
                start_time = hash_data_multiple[0]["blockTimestamp"]
                usd_value = hash_data_multiple[0]["historicalUSD"]

                if start_time is None or usd_value is None:
                    error_message = "Error with the input hash or blockchain not supported."
                else:
                    transfers_data = arkham_transfers(headers, start_time, usd_value)
                    if 'error' in transfers_data:
                        error_message = transfers_data['error']
                    else:
                        transfers_multiple_pre = transfers_data.get('transfers', [])
                        transfers_multiple = []

                        for transfer in transfers_multiple_pre:
                            original_hash_timestamp_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                            original_hash_timestamp = int(original_hash_timestamp_dt.timestamp() * 1000)
                            transfer_timestamp_dt = datetime.strptime(transfer["blockTimestamp"], "%Y-%m-%dT%H:%M:%SZ")
                            transfer_timestamp = int(transfer_timestamp_dt.timestamp() * 1000)
                            if transfer_timestamp > original_hash_timestamp:
                                transfers_multiple.append(transfer)

                        for transfer in transfers_multiple:
                            dict_keys = (list(transfer.keys()))
                            if 'transactionHash' in dict_keys and transfer['transactionHash'] not in hashes:
                                multi_hash_data.append({
                                    "blockchain": transfer['chain'],
                                    "hash": transfer['transactionHash'],
                                    "from": transfer['fromAddress']['address'],
                                    "to": transfer['toAddress']['address'],
                                    "unitValue": transfer['unitValue'],
                                    "tokenSymbol": transfer['tokenSymbol'],
                                    "historicalUSD": transfer['historicalUSD'],
                                })
                            elif 'txid' in dict_keys and transfer['txid'] not in hashes: # BTC blockchain
                                for address in transfer['toAddresses']:
                                    multi_hash_data.append({
                                        "blockchain": transfer['fromAddress']['chain'],
                                        "hash": transfer['txid'],
                                        "from": transfer['fromAddress']['address'],
                                        "to": address['address']['address'],
                                        "unitValue": transfer['unitValue'],
                                        "tokenSymbol": 'BTC',
                                        "historicalUSD": transfer["historicalUSD"],
                                    })
        
        count_reps = {}
        hashes_to = {}
        for element in multi_hash_data:
            to_address = element["to"]
            if to_address in count_reps:
                count_reps[to_address] += 1
                hashes_to[to_address].append(element['hash'])
            else:
                count_reps[to_address] = 1
                hashes_to[to_address] = []
                hashes_to[to_address].append(element['hash'])
                
        
        agregated_addresses = set()
        for hash in multi_hash_data:
            to_address = hash['to']
            if to_address not in agregated_addresses:
                new_element = {k: hash[k] for k in ("blockchain", "to")}
                new_element["repetitions"] = count_reps[to_address]
                new_element["hashes"] = hashes_to[to_address]

                address_list.append(new_element)
                agregated_addresses.add(to_address)

        address_list.sort(key = lambda x: x["repetitions"], reverse = True)

    return render_template('index.html', hash_data=hash_data, transfers=transfers, address_list=address_list, hashes_data=hashes_data, error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True)