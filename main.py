from pathlib import Path
import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "agreement_clean.txt"
OUTPUT_PATH = BASE_DIR / "agreement_filled.txt"


class ContractData(BaseModel):
    contract_number: str
    city: str
    contract_day: str
    contract_month: str
    contract_year: str

    customer_company_name: str
    customer_representative_name: str
    customer_representative_basis: str
    customer_inn: str
    customer_ogrn_or_ogrnip: str
    customer_legal_address: str
    customer_bank: str
    customer_bik: str
    customer_correspondent_account: str
    customer_settlement_account: str

    contractor_company_name: str
    contractor_representative_name: str
    contractor_representative_basis: str
    contractor_inn: str
    contractor_ogrn_or_ogrnip: str
    contractor_legal_address: str
    contractor_bank: str
    contractor_bik: str
    contractor_correspondent_account: str
    contractor_settlement_account: str

    vat_type: str


def render_contract_template(template_text: str, payload: dict) -> str:
    """
    Replace placeholders like {{ field_name }} with values from payload.
    Unknown placeholders are replaced with an empty string.
    """

    def replacer(match: re.Match) -> str:
        field_name = match.group(1).strip()
        value = payload.get(field_name, "")
        return str(value)

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replacer, template_text)


@app.post("/generate-contract")
def generate_contract(data: ContractData):
    payload = data.model_dump()

    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Template file agreement_clean.txt not found")

    try:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read template file: {exc}") from exc

    rendered_text = render_contract_template(template_text, payload)

    try:
        OUTPUT_PATH.write_text(rendered_text, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write agreement_filled.txt: {exc}") from exc

    return {
        "status": "ok",
        "message": "Contract generated successfully",
        "output_file": str(OUTPUT_PATH.name),
    }
