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

    contractor_type: str
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


def extract_template_variables(template_text: str) -> set[str]:
    return set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", template_text))


def inflect_fio_case(full_name: str, _: str) -> str:
    """
    Без внешней морфологии: возвращаем исходное ФИО.
    Это убирает зависимость от pkg_resources/setuptools.
    """
    return full_name or ""


def build_context(payload: dict) -> dict:
    fio = payload.get("contractor_representative_name", "")
    return {
        **payload,
        "contractor_fio_nominative": fio,
        "contractor_fio_genitive": inflect_fio_case(fio, "gent"),
        "contractor_fio_dative": inflect_fio_case(fio, "datv"),
        "contractor_fio_instrumental": inflect_fio_case(fio, "ablt"),
    }


def render_template(template_text: str, context: dict) -> str:
    rendered = template_text

    def if_replacer(match: re.Match) -> str:
        var_name = match.group(1)
        expected_value = match.group(2)
        block = match.group(3)
        return block if str(context.get(var_name, "")) == expected_value else ""

    rendered = re.sub(
        r"\{%\s*if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*==\s*\"([^\"]+)\"\s*%\}(.*?)\{%\s*endif\s*%\}",
        if_replacer,
        rendered,
        flags=re.DOTALL,
    )

    def var_replacer(match: re.Match) -> str:
        name = match.group(1)
        return str(context.get(name, ""))

    rendered = re.sub(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", var_replacer, rendered)
    return rendered


@app.post("/generate-contract")
def generate_contract(data: ContractData):
    payload = data.model_dump()

    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Template file agreement_clean.txt not found")

    try:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read template file: {exc}") from exc

    context = build_context(payload)

    required_vars = extract_template_variables(template_text)
    missing_vars = sorted(var for var in required_vars if var not in context)
    if missing_vars:
        raise HTTPException(
            status_code=500,
            detail=f"Template has unresolved variables: {', '.join(missing_vars)}",
        )

    rendered_text = render_template(template_text, context)

    try:
        OUTPUT_PATH.write_text(rendered_text, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write agreement_filled.txt: {exc}") from exc

    return {
        "status": "ok",
        "message": "Contract generated successfully",
        "output_file": OUTPUT_PATH.name,
        "morphology_engine": "disabled",
    }
