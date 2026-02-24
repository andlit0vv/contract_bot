from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

saved_contract_data = None


class ContractData(BaseModel):
    data: dict


@app.post("/save-contract")
def save_contract(data: ContractData):
    global saved_contract_data
    saved_contract_data = data.data
    return {"status": "ok"}


@app.get("/get-contract")
def get_contract():
    return saved_contract_data
