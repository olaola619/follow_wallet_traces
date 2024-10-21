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

def arkham_transfers_asc(headers, start_time_str, usd_value, percent_above, percent_below, entities):
    url = "https://api.arkhamintelligence.com/transfers"
    str_time_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
    # str_time_dt += timedelta(minutes = 1)
    start_time = int(str_time_dt.timestamp() * 1000)
    
    params = {
        # "base": ["fixedfloat", "changenow", "simpleswap", "0xEbA88149813BEc1cCcccFDb0daCEFaaa5DE94cB1"],
        "base": entities,
        "flow": "out",
        "timeGte": start_time,
        "sortKey": "time",
        "sortDir": "asc",
        "usdLte": usd_value * percent_below,
        "usdGte": usd_value * percent_above,
        "limit": 50
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error in API request: {response.status_code}"}

def arkham_transfers_desc(headers, end_time_str, usd_value, percent_above, percent_below, entities):
    url = "https://api.arkhamintelligence.com/transfers"
    str_time_dt = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M:%SZ")
    # str_time_dt += timedelta(minutes = 1)
    end_time = int(str_time_dt.timestamp() * 1000)
    
    params = {
        # "base": ["fixedfloat", "changenow", "simpleswap", "0xEbA88149813BEc1cCcccFDb0daCEFaaa5DE94cB1"],
        "base": entities,
        "flow": "in",
        "timeLte": end_time,
        "sortKey": "time",
        "sortDir": "desc",
        "usdLte": usd_value * percent_below,
        "usdGte": usd_value * percent_above,
        "limit": 50
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
    error_display = None

    try:
        if request.method == 'POST' and 'hash' in request.form:
            # API headers
            api_key = request.form.get('api_key')
            headers = {
                "API-Key": api_key
            }
            percent_above = (100 - float(request.form.get('percent_above'))) / 100
            percent_below = (100 + float(request.form.get('percent_below'))) / 100
            dif_minutes = int(request.form.get('minutes'))
            destination = request.form.get('destination')
            entities = request.form.get('entities')
            entities = entities.splitlines()

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
                limit_time = hash_data[0]["blockTimestamp"]
                usd_value = hash_data[0]["historicalUSD"]
                if limit_time is None or usd_value is None:
                    error_message = "Error with the input hash or blockchain not supported."
                else:
                    if destination == 'To':
                        transfers_data = arkham_transfers_asc(headers, limit_time, usd_value, percent_above, percent_below, entities)
                    else:
                        transfers_data = arkham_transfers_desc(headers, limit_time, usd_value, percent_above, percent_below, entities)
                    if 'error' in transfers_data:
                        error_message = transfers_data['error']
                    else:
                        transfers_pre = transfers_data.get('transfers', [])
                        for transfer in transfers_pre:
                            original_hash_timestamp_dt = datetime.strptime(limit_time, "%Y-%m-%dT%H:%M:%SZ")
                            original_hash_timestamp = int(original_hash_timestamp_dt.timestamp() * 1000)
                            transfer_timestamp_dt = datetime.strptime(transfer["blockTimestamp"], "%Y-%m-%dT%H:%M:%SZ")
                            transfer_timestamp = int(transfer_timestamp_dt.timestamp() * 1000)
                            if destination == 'To' and transfer_timestamp > original_hash_timestamp and transfer_timestamp < (original_hash_timestamp + dif_minutes * 60000) and transfer.get("toIsContract", None) == False:
                                transfers.append(transfer)
                            elif destination == 'From' and transfer_timestamp < original_hash_timestamp and transfer_timestamp > (original_hash_timestamp - dif_minutes * 60000) and transfer.get("fromIsContract", None) == False:
                                transfers.append(transfer)
    except Exception as e:
        error_display = "There were an error, check the console for logs"
        error_message = e

    # Find most common addresses
    address_list = []
    transfers_multiple = []
    hashes_data = []

    try:
        if request.method == 'POST' and 'hashes' in request.form:
            # API headers
            api_key = request.form.get('api_key')
            headers = {
                "API-Key": api_key
            }
            percent_above = (100 - float(request.form.get('percent_above'))) / 100
            percent_below = (100 + float(request.form.get('percent_below'))) / 100
            dif_minutes = int(request.form.get('minutes'))
            destination = request.form.get('destination')
            entities = request.form.get('entities')
            entities = entities.splitlines()

            # Multiple Hashes
            hashes_input = request.form.get('hashes')
            hashes = hashes_input.splitlines()
            hashes = list(set(hashes))  # Eliminate duplicates
            multi_hash_data = []
            uniq_hashes = []

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
                    limit_time = hash_data_multiple[0]["blockTimestamp"]
                    usd_value = hash_data_multiple[0]["historicalUSD"]

                    if limit_time is None or usd_value is None:
                        error_message = "Error with the input hash or blockchain not supported."
                    else:
                        if destination == 'To':
                            transfers_data = arkham_transfers_asc(headers, limit_time, usd_value, percent_above, percent_below, entities)
                        else:
                            transfers_data = arkham_transfers_desc(headers, limit_time, usd_value, percent_above, percent_below, entities)
                        if 'error' in transfers_data:
                            error_message = transfers_data['error']
                        else:
                            transfers_multiple_pre = transfers_data.get('transfers', [])
                            transfers_multiple = []

                            for transfer in transfers_multiple_pre:
                                original_hash_timestamp_dt = datetime.strptime(limit_time, "%Y-%m-%dT%H:%M:%SZ")
                                original_hash_timestamp = int(original_hash_timestamp_dt.timestamp() * 1000)
                                transfer_timestamp_dt = datetime.strptime(transfer["blockTimestamp"], "%Y-%m-%dT%H:%M:%SZ")
                                transfer_timestamp = int(transfer_timestamp_dt.timestamp() * 1000)
                                if destination == 'To' and transfer_timestamp > original_hash_timestamp and transfer_timestamp < (original_hash_timestamp + dif_minutes * 60000) and transfer.get("toIsContract", None) == False:
                                    transfers_multiple.append(transfer)
                                elif destination == 'From' and transfer_timestamp < original_hash_timestamp and transfer_timestamp > (original_hash_timestamp - dif_minutes * 60000) and transfer.get("fromIsContract", None) == False:
                                    transfers_multiple.append(transfer)

                            for transfer in transfers_multiple:
                                dict_keys = (list(transfer.keys()))
                                if 'transactionHash' in dict_keys and transfer['transactionHash'] not in hashes and transfer['transactionHash'] not in uniq_hashes:
                                    multi_hash_data.append({
                                        "blockchain": transfer['chain'],
                                        "hash": transfer['transactionHash'],
                                        "from": transfer['fromAddress']['address'],
                                        "to": transfer['toAddress']['address'],
                                        "unitValue": transfer['unitValue'],
                                        "tokenSymbol": transfer['tokenSymbol'],
                                        "historicalUSD": transfer['historicalUSD'],
                                        "blockTimestamp": transfer['blockTimestamp'],
                                    })
                                    uniq_hashes.append(transfer['transactionHash'])
                                elif 'txid' in dict_keys and transfer['txid'] not in hashes and transfer['txid'] not in uniq_hashes: # BTC blockchain
                                    for address in transfer['toAddresses']:
                                        multi_hash_data.append({
                                            "blockchain": transfer['fromAddress']['chain'],
                                            "hash": transfer['txid'],
                                            "from": transfer['fromAddress']['address'],
                                            "to": address['address']['address'],
                                            "unitValue": transfer['unitValue'],
                                            "tokenSymbol": 'BTC',
                                            "historicalUSD": transfer["historicalUSD"],
                                            "blockTimestamp": transfer['blockTimestamp'],
                                        })
                                        uniq_hashes.append(transfer['txid'])
            
            count_reps = {}
            hashes_to = {}
            for element in multi_hash_data:
                to_address = element["to"]
                if to_address in count_reps:
                    count_reps[to_address] += 1
                    hashes_to[to_address].append({
                        "hash": element['hash'],
                        "historicalUSD": element['historicalUSD'],
                        "blockTimestamp": element['blockTimestamp'],
                        })
                else:
                    count_reps[to_address] = 1
                    hashes_to[to_address] = []
                    hashes_to[to_address].append({
                        "hash": element['hash'],
                        "historicalUSD": element['historicalUSD'],
                        "blockTimestamp": element['blockTimestamp'],
                        })
                    
            
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
    except Exception as e:
        error_display = "There were an error, check the console for logs"
        error_message = e

    return render_template('index.html', hash_data=hash_data, transfers=transfers, address_list=address_list, hashes_data=hashes_data, error_message=error_message, error_display=error_display)

if __name__ == '__main__':
    app.run(debug=True)