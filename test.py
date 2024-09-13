import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import requests


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

def arkham_request(url, headers, params=None):
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error in API request: {response.status_code}"}

def arkham_transfer_hash(hash, chain, transferType, headers):
    url = f"https://api.arkhamintelligence.com/transfers/tx/{hash}"

    params = {
        "chain": chain,
        "transferType": transferType,
    }

    response = arkham_request(url, headers=headers, params=params)
    return response

# API headers
headers = {
    "API-Key": api_key
}

data = arkham_transfer_hash("0x86422a9bb2bdb23b258d34b846fdefc7810ed7cbbe4d4075f2ef1ac95b6c9069", 'bsc', 'token', headers)
print("hi")