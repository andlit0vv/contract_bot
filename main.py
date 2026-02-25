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


# -----------------------
# TEMPLATE ENGINE
# -----------------------

def extract_template_variables(template_text: str) -> set[str]:
    return set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", template_text))


def inflect_word(word: str, case: str) -> str:
    """
    Простое склонение русских ФИО без библиотек.
    case: gent (Р.п.), datv (Д.п.), ablt (Т.п.)
    """

    if not word:
        return word

    # -------- ФАМИЛИИ --------
    if word.endswith("ов") or word.endswith("ев") or word.endswith("ин"):
        if case == "gent":
            return word + "а"
        if case == "datv":
            return word + "у"
        if case == "ablt":
            return word + "ым"

    if word.endswith("ова") or word.endswith("ева") or word.endswith("ина"):
        if case == "gent":
            return word[:-1] + "ой"
        if case == "datv":
            return word[:-1] + "ой"
        if case == "ablt":
            return word[:-1] + "ой"

    # -------- ИМЕНА --------
    if word.endswith("й"):
        base = word[:-1]
        if case == "gent":
            return base + "я"
        if case == "datv":
            return base + "ю"
        if case == "ablt":
            return base + "ем"

    if word.endswith("а"):
        base = word[:-1]
        if case == "gent":
            return base + "ы"
        if case == "datv":
            return base + "е"
        if case == "ablt":
            return base + "ой"

    if word.endswith("я"):
        base = word[:-1]
        if case == "gent":
            return base + "и"
        if case == "datv":
            return base + "е"
        if case == "ablt":
            return base + "ей"

    # -------- ОТЧЕСТВА --------
    if word.endswith("ич"):
        if case == "gent":
            return word + "а"
        if case == "datv":
            return word + "у"
        if case == "ablt":
            return word + "ем"

    if word.endswith("на"):
        base = word[:-1]
        if case == "gent":
            return base + "ы"
        if case == "datv":
            return base + "е"
        if case == "ablt":
            return base + "ой"

    # fallback
    return word


def inflect_fio_case(full_name: str, case: str) -> str:
    if not full_name:
        return ""

    if case == "nomn":
        return full_name

    parts = full_name.split()
    inflected = [inflect_word(p, case) for p in parts]
    return " ".join(inflected)


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

    # Проверка переменных
    required_vars = extract_template_variables(template_text)
    missing = [v for v in required_vars if v not in context]

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing variables: {', '.join(missing)}",
        )

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
