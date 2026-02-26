from pathlib import Path
import json
import os
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI
from openai import OpenAI
from pydantic import BaseModel

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "agreement_clean.txt"
OUTPUT_PATH = BASE_DIR / "agreement_filled.txt"

SYSTEM_PROMPT = """You are a legally oriented system analyst.
Based on the project description, generate strictly valid JSON.
No text outside JSON.
No comments.
No explanations.
Do not add new fields.
Structure must match exactly.

{
  "subject_clause": "string",
  "ip_transfer_clause": "string",
  "estimated_duration_days": "integer",
  "estimated_total_cost": "string",
  "prepayment_percent": "number",
  "stages": [
    {
      "name": "string",
      "description": "string",
      "payment_percent": "number"
    }
  ],
  "penalty_for_delay_percent_per_day": "number",
  "penalty_cap_percent": "number",
  "warranty_months": "integer"
}"""


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


def to_initials(full_name: str) -> str:
    parts = [part for part in full_name.split() if part]
    if not parts:
        return ""
    surname = parts[0]
    initials = "".join(f"{p[0]}." for p in parts[1:] if p)
    return f"{surname} {initials}".strip()


def _format_stage(stage: dict[str, Any], index: int) -> str:
    return f"Этап {index}: {stage['name']} — {stage['description']} ({stage['payment_percent']}%)"


def _ru_percent_word(value: float) -> str:
    n = int(value)
    n10 = n % 10
    n100 = n % 100
    if n10 == 1 and n100 != 11:
        return "процент"
    if n10 in (2, 3, 4) and n100 not in (12, 13, 14):
        return "процента"
    return "процентов"


def _ru_months_word(value: int) -> str:
    n10 = value % 10
    n100 = value % 100
    if n10 == 1 and n100 != 11:
        return "месяц"
    if n10 in (2, 3, 4) and n100 not in (12, 13, 14):
        return "месяца"
    return "месяцев"


def _ru_days_word(value: int) -> str:
    n10 = value % 10
    n100 = value % 100
    if n10 == 1 and n100 != 11:
        return "день"
    if n10 in (2, 3, 4) and n100 not in (12, 13, 14):
        return "дня"
    return "дней"


def request_llm_contract_vars(project_description: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    if not project_description.strip():
        raise HTTPException(status_code=422, detail="project_description is required")

    client = OpenAI(api_key=api_key)
    user_prompt = f"Project description:\n{project_description}"

    for _ in range(2):
        try:
            completion = client.responses.create(
                model="gpt-5-mini",
                temperature=0,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except (APIConnectionError, APITimeoutError):
            raise HTTPException(status_code=502, detail="OpenAI API connection error")
        except APIError as exc:
            raise HTTPException(status_code=502, detail=f"OpenAI API error: {exc.__class__.__name__}")
        completion = client.responses.create(
            model="gpt-5-mini",
            temperature=0,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        text = completion.output_text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue

    raise HTTPException(status_code=502, detail="Failed to parse model JSON response")


def validate_llm_json(data: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = {
        "subject_clause": str,
        "ip_transfer_clause": str,
        "estimated_duration_days": int,
        "estimated_total_cost": str,
        "prepayment_percent": (int, float),
        "stages": list,
        "penalty_for_delay_percent_per_day": (int, float),
        "penalty_cap_percent": (int, float),
        "warranty_months": int,
    }

    missing = set(allowed_fields) - set(data)
    extra = set(data) - set(allowed_fields)
    if missing or extra:
        raise HTTPException(status_code=422, detail=f"Invalid JSON structure: missing={sorted(missing)}, extra={sorted(extra)}")

    for field, field_type in allowed_fields.items():
        if not isinstance(data[field], field_type):
            raise HTTPException(status_code=422, detail=f"Invalid type for field: {field}")

    stages = data["stages"]
    if not (2 <= len(stages) <= 5):
        raise HTTPException(status_code=422, detail="stages length must be from 2 to 5")

    stage_percent_sum = 0.0
    for stage in stages:
        if not isinstance(stage, dict):
            raise HTTPException(status_code=422, detail="Each stage must be an object")
        stage_required = {"name": str, "description": str, "payment_percent": (int, float)}
        stage_missing = set(stage_required) - set(stage)
        stage_extra = set(stage) - set(stage_required)
        if stage_missing or stage_extra:
            raise HTTPException(status_code=422, detail="Each stage must contain only name, description, payment_percent")
        for stage_field, stage_type in stage_required.items():
            if not isinstance(stage[stage_field], stage_type):
                raise HTTPException(status_code=422, detail=f"Invalid type in stage field: {stage_field}")
        stage_percent_sum += float(stage["payment_percent"])

    if abs(stage_percent_sum - 100.0) > 1e-6:
        raise HTTPException(status_code=422, detail="sum(stage.payment_percent) must equal 100")

    if not (30 <= float(data["prepayment_percent"]) <= 50):
        raise HTTPException(status_code=422, detail="prepayment_percent must be between 30 and 50")

    if not (2 <= data["warranty_months"] <= 6):
        raise HTTPException(status_code=422, detail="warranty_months must be between 2 and 6")

    if not (0.1 <= float(data["penalty_for_delay_percent_per_day"]) <= 0.5):
        raise HTTPException(status_code=422, detail="penalty_for_delay_percent_per_day must be between 0.1 and 0.5")

    if float(data["penalty_cap_percent"]) != 10.0:
        raise HTTPException(status_code=422, detail="penalty_cap_percent must equal 10")

    return data


def build_context(payload: dict, llm_json_fields: dict[str, Any]) -> dict:
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

    stages_render = [_format_stage(stage, idx + 1) for idx, stage in enumerate(llm_json_fields["stages"])]

    return {
        **payload,
        **llm_json_fields,
        "product_genitive": "программного обеспечения",
        "customer_representative_name_genitive": inflect_fio_case(customer_fio, "gent"),
        "contractor_fio_full": fio,
        "contractor_ogrnip": payload.get("contractor_ogrn_or_ogrnip", ""),
        "work_scope": project_points,
        "customer_ogrn": payload.get("customer_ogrn_or_ogrnip", ""),
        "customer_kpp": payload.get("customer_kpp", "Не указано"),
        "contractor_address": payload.get("contractor_legal_address", ""),
        "contractor_fio_nominative": fio,
        "contractor_fio_genitive": inflect_fio_case(fio, "gent"),
        "contractor_fio_dative": inflect_fio_case(fio, "datv"),
        "contractor_fio_instrumental": inflect_fio_case(fio, "ablt"),
        "contractor_intro_name": contractor_intro,
        "stages": stages_render,
        "prepayment_percent_word": _ru_percent_word(float(llm_json_fields["prepayment_percent"])),
        "penalty_for_delay_percent_per_day_word": _ru_percent_word(float(llm_json_fields["penalty_for_delay_percent_per_day"])),
        "penalty_cap_percent_word": _ru_percent_word(float(llm_json_fields["penalty_cap_percent"])),
        "warranty_months_word": _ru_months_word(int(llm_json_fields["warranty_months"])),
        "estimated_duration_days_word": _ru_days_word(int(llm_json_fields["estimated_duration_days"])),
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

    llm_json = request_llm_contract_vars(payload.get("project_description", ""))
    validated_llm_json = validate_llm_json(llm_json)
    context = build_context(payload, validated_llm_json)

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
        "morphology": "disabled",
    }
