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
    customer_kpp: str = "Не указано"

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
    project_description: str = ""


# -----------------------
# TEMPLATE ENGINE
# -----------------------

def extract_template_variables(template_text: str) -> set[str]:
    return set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", template_text))


def to_initials(full_name: str) -> str:
    parts = [part for part in full_name.split() if part]
    if not parts:
        return ""
    surname = parts[0]
    initials = "".join(f"{p[0]}." for p in parts[1:] if p)
    return f"{surname} {initials}".strip()


def build_context(payload: dict) -> dict:
    fio = payload.get("contractor_representative_name", "")
    customer_fio = payload.get("customer_representative_name", "")
    project_description = payload.get("project_description", "")
    project_points = [item.strip(" -\t") for item in project_description.split(";") if item.strip()]
    if not project_points and project_description.strip():
        project_points = [project_description.strip()]
    if not project_points:
        project_points = ["Объем работ уточняется в техническом задании."]

    contractor_intro = f"{payload.get('contractor_type', '')} {fio}".strip()
    if payload.get("contractor_type") == "ИП":
        contractor_intro = f"ИП {to_initials(fio)}".strip()

    return {
        **payload,
        "product_genitive": "программного обеспечения",
        "customer_representative_name_genitive": customer_fio,
        "contractor_fio_full": fio,
        "contractor_ogrnip": payload.get("contractor_ogrn_or_ogrnip", ""),
        "work_scope": project_points,
        "customer_ogrn": payload.get("customer_ogrn_or_ogrnip", ""),
        "customer_kpp": payload.get("customer_kpp", "Не указано"),
        "contractor_address": payload.get("contractor_legal_address", ""),
        "contractor_fio_nominative": fio,
        "contractor_fio_genitive": fio,
        "contractor_fio_dative": fio,
        "contractor_fio_instrumental": fio,
        "contractor_intro_name": contractor_intro,
    }


def render_template(template_text: str, context: dict) -> str:
    rendered = template_text

    # {% for item in work_scope %}...{{ item }}...{% endfor %}
    def for_replacer(match: re.Match) -> str:
        loop_var = match.group(1)
        iterable_name = match.group(2)
        block = match.group(3)
        iterable = context.get(iterable_name, [])
        if not isinstance(iterable, list):
            return ""

        chunks = []
        for value in iterable:
            chunks.append(re.sub(r"\{\{\s*" + re.escape(loop_var) + r"\s*\}\}", str(value), block))
        return "".join(chunks)

    rendered = re.sub(
        r"\{%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}(.*?)\{%\s*endfor\s*%\}",
        for_replacer,
        rendered,
        flags=re.DOTALL,
    )

    # {% if var == "value" %}
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

    # {{ variable }}
    def var_replacer(match: re.Match) -> str:
        name = match.group(1)
        return str(context.get(name, ""))

    rendered = re.sub(
        r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}",
        var_replacer,
        rendered,
    )

    return rendered


# -----------------------
# API
# -----------------------

@app.post("/generate-contract")
def generate_contract(data: ContractData):
    payload = data.model_dump()

    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Template not found")

    try:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    context = build_context(payload)

    required_vars = extract_template_variables(template_text)
    for var_name in required_vars:
        context.setdefault(var_name, "")

    rendered = render_template(template_text, context)

    try:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "ok",
        "output_file": OUTPUT_PATH.name,
        "morphology": "disabled"
    }
