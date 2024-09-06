import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"  # Reset color

os.system('cls')

# Load env file
load_dotenv()
api_key = os.getenv('API_KEY')

if api_key is None:
    api_key = input("Introduce the api key: ")

# API Key
headers = {
    "API-Key": api_key
}

def arkham_request(url, params = None):
    # Request
    response = requests.get(url, headers=headers, params=params)

    # Check if successfull request
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error in API request: {response.status_code}")  


def arkham_hash(hash):

    # URL hash
    url = f"https://api.arkhamintelligence.com/tx/{hash}"

    hash_info = arkham_request(url)

    return hash_info

def arkham_transfers(start_time_str, usd_value, cex = True, sc = True):
    # URL base
    url = "https://api.arkhamintelligence.com/transfers"

    # Request parameters
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

    # Request
    response = requests.get(url, headers=headers, params=params)

    # Check if successfull request
    if response.status_code == 200:
        data = response.json()
        
        # Display Txs
        if data.get("transfers"):
            for tx in data["transfers"]:
                print_out_tx(tx)
        else:
            print("No incoming transactions found in the specified period.")
    else:
        print(f"Error in API request: {response.status_code}")

def print_out_tx(tx):
    dict_keys = (list(tx.keys()))
    if 'transactionHash' in dict_keys:
        print(f"{YELLOW}Blockchain: {tx['chain']}{RESET}")
        print(f"Transaction Hash: {tx['transactionHash']}")
        print(f"From: {tx['fromAddress']['address']}")
        print(f"To: {tx['toAddress']['address']}")
        print(f"Token: {tx['tokenName']}")
        print(f"Amount: {tx['unitValue']} {tx['tokenSymbol']} = {GREEN}${tx['historicalUSD']}{RESET}")
        print(f"{MAGENTA}Date: {tx['blockTimestamp']}{RESET}")
        print("-" * 40)
    elif 'txid' in dict_keys: # BTC blockchain
        print(f"{YELLOW}Blockchain: {tx['fromAddress']['chain']}{RESET}")
        print(f"Transaction Hash: {tx['txid']}")
        print(f"From: {tx['fromAddress']['address']}")
        for address in tx['toAddresses']:
            print(f"To: {address['address']['address']}: {address['value']} BTC")
        print(f"Amount: {tx['unitValue']} BTC = {GREEN}${tx['historicalUSD']}{RESET}")
        print(f"{MAGENTA}Date: {tx['blockTimestamp']}{RESET}")
        print("-" * 40)

def print_in_tx(hash_data):
    # In case the hash was in more than one blockchain (Weird)
    blockchains_list = list(hash_data.keys())

    for blockchain in blockchains_list:
        if blockchain == 'tron':
            print(f"{RED}TRON AS INPUT NOT SUPPORTED{RESET}\n")
            print("-" * 40)
            return None, None
        elif blockchain == 'bitcoin':
            print(f"{BLUE}INPUT{RESET}\n")
            print(f"{YELLOW}Blockchain: {blockchain}{RESET}")
            print(f"Transaction Hash: {hash_data[blockchain]['txid']}")
            print(f"To: {hash_data[blockchain]['outputs'][0]['address']['address']}")
            print(f"Token: BTC")
            print(f"Amount: {hash_data[blockchain]['outputValue']} BTC = {GREEN}${hash_data[blockchain]['outputUSD']}{RESET}")
            print(f"{MAGENTA}Date: {hash_data[blockchain]['blockTimestamp']}{RESET}")
            print("-" * 40)
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['outputUSD']
        else:
            print(f"{BLUE}INPUT{RESET}\n")
            print(f"{YELLOW}Blockchain: {blockchain}{RESET}")
            print(f"Transaction Hash: {hash_data[blockchain]['hash']}")
            print(f"From: {hash_data[blockchain]['fromAddress']}")
            print(f"To: {hash_data[blockchain]['toAddress']}")
            print(f"Token: {hash_data[blockchain]['tokenID']}")
            print(f"Amount: {hash_data[blockchain]['unitValue']} {hash_data[blockchain]['tokenSymbol']} = {GREEN}${hash_data[blockchain]['usdValue']}{RESET}")
            print(f"{MAGENTA}Date: {hash_data[blockchain]['blockTimestamp']}{RESET}")
            print("-" * 40)
            return hash_data[blockchain]['blockTimestamp'], hash_data[blockchain]['usdValue']

def main():
    print(f"{YELLOW}FIND THE DESTINATION WALLETS FROM FF, SS AND CN{RESET}")

    while True:
        hash = input("\nIntroduce the input hash ([F] to finish): ")
        print("")
        if hash.upper() == 'F':
                break
        
        hash_data = arkham_hash(hash)

        start_time, usd_value = print_in_tx(hash_data)

        if (start_time == None or usd_value == None):
            print(f"{RED}There were an error with the input hash or blockchain not supported!{RESET}")
            return
        
        print(f"\n{BLUE}OUTPUT{RESET}\n")
        arkham_transfers(start_time, usd_value) 

main()