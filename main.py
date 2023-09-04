import datetime
import json
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pymongo.mongo_client import MongoClient
from web3 import Web3

app = FastAPI()

load_dotenv()
USERNAME = os.getenv("MONGO_USER_NAME")
PASSWORD = os.getenv('MONGO_USER_PASS')
dburi = f'mongodb+srv://{USERNAME}:{PASSWORD}@testing-db.l2k9oyr.mongodb.net/?retryWrites=true&w=majority'

mongo_client = MongoClient(dburi)

try:
    mongo_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = mongo_client['crv_balance']
collection = db['balances']

with open("token_abi.json") as crv:
    abii = json.load(crv)

web3 = Web3(Web3.HTTPProvider("https://eth.public-rpc.com/"))

wallet_address = "0x326D9f47BA49BBAac279172634827483af70a601"
crv_contract_address = "0xD533a949740bb3306d119CC777fa900bA034cd52"

url = f'https://api.coingecko.com/api/v3/simple/token_price/ethereum?contract_addresses={crv_contract_address}&vs_currencies=usd'


@app.get("/")
def read_root():
    return {"message": "CRV Balance API"}


@app.get("/balance")
async def get_balance(wallet: str):
    try:

        token = web3.eth.contract(address=Web3.to_checksum_address(crv_contract_address),
                                  abi=abii)  # declaring the token contract

        token_balance = token.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
        token_balance = token_balance / (10 ** 18)

        response = requests.get(url)
        data = response.json()

        usd_value = list(data.values())[0]['usd']

        collection.insert_one({
            "wallet": Web3.to_checksum_address(wallet),
            "total_usd_balance": token_balance * usd_value,
            "crv_balance": token_balance,
            "current_timestamp":datetime.datetime.now().isoformat()
        })

        return {"message": " Succesffully added" }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def serialize_document(document):
    # Convert ObjectId to string
    document['_id'] = str(document['_id'])
    return document


@app.get("/balance-history")
async def get_balance_history(wallet: str):
    print(wallet)

    cursor = collection.find({"wallet": Web3.to_checksum_address(wallet)})

    # Convert the cursor to a list and serialize each document
    history = [serialize_document(doc) for doc in cursor]
    return {"result": history}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
