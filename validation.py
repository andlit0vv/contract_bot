from __future__ import annotations

import json
from typing import Any


class ValidationError(ValueError):
    """Raised when the LLM JSON payload does not match expected rules."""


EXPECTED_KEYS = {
    "project_summary",
    "product_type",
    "work_scope_items",
    "total_duration_working_days",
    "stages_count",
    "stages",
    "prepayment_percent",
    "ip_transfer_model",
    "access_transfer_required",
    "penalty_percent_per_day",
    "penalty_cap_percent",
    "warranty_claim_window_months",
}


DEFAULT_STAGE_NAMES = ["Аналитика", "Разработка", "Тестирование и запуск"]
DEFAULT_STAGE_DURATIONS = [40, 35, 35]
DEFAULT_STAGE_PAYMENTS = [50, 30, 20]


def parse_and_validate_project_json(raw_text: str) -> dict[str, Any]:
    """Parse LLM response text, normalize template-locked fields, validate payload."""
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"LLM response is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValidationError("Top-level JSON must be an object.")

    _validate_structure(payload)
    normalized_payload = _normalize_payload(payload)
    _validate_business_logic(normalized_payload)
    return normalized_payload


def _validate_structure(payload: dict[str, Any]) -> None:
    payload_keys = set(payload.keys())
    if payload_keys != EXPECTED_KEYS:
        missing = sorted(EXPECTED_KEYS - payload_keys)
        extra = sorted(payload_keys - EXPECTED_KEYS)
        raise ValidationError(
            f"Invalid JSON schema. Missing keys: {missing}. Extra keys: {extra}."
        )

    if not isinstance(payload["work_scope_items"], list) or not payload["work_scope_items"]:
        raise ValidationError("work_scope_items must be a non-empty array.")
    if not isinstance(payload["stages"], list) or not payload["stages"]:
        raise ValidationError("stages must be a non-empty array.")

    for idx, stage in enumerate(payload["stages"], start=1):
        if not isinstance(stage, dict):
            raise ValidationError(f"Stage #{idx} must be an object.")

        stage_keys = set(stage.keys())
        required_stage_keys = {"name", "duration_working_days", "payment_percent"}
        if stage_keys != required_stage_keys:
            raise ValidationError(
                f"Stage #{idx} must contain only {sorted(required_stage_keys)}"
            )


def _to_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return int(value)
    return default


def _normalize_sum(values: list[int], target: int, min_each: int) -> list[int]:
    """Normalize list to integer target while keeping each >= min_each."""
    n = len(values)
    if n == 0:
        return []

    safe = [max(min_each, _to_int(v, min_each)) for v in values]
    total = sum(safe)
    if total <= 0:
        base = target // n
        result = [max(min_each, base) for _ in range(n)]
    else:
        result = [max(min_each, int(v * target / total)) for v in safe]

    diff = target - sum(result)
    step = 1 if diff > 0 else -1
    idx = 0
    while diff != 0:
        i = idx % n
        if step > 0 or result[i] > min_each:
            result[i] += step
            diff -= step
        idx += 1

    return result


def _normalize_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_input = []
    for stage in stages:
        normalized_input.append(
            {
                "name": str(stage.get("name") or ""),
                "duration_working_days": _to_int(stage.get("duration_working_days"), 1),
                "payment_percent": _to_int(stage.get("payment_percent"), 1),
            }
        )

    if len(normalized_input) >= 3:
        base = normalized_input[:3]
        for extra in normalized_input[3:]:
            base[2]["duration_working_days"] += max(1, extra["duration_working_days"])
            base[2]["payment_percent"] += max(1, extra["payment_percent"])
    else:
        base = normalized_input

    while len(base) < 3:
        idx = len(base)
        base.append(
            {
                "name": DEFAULT_STAGE_NAMES[idx],
                "duration_working_days": DEFAULT_STAGE_DURATIONS[idx],
                "payment_percent": DEFAULT_STAGE_PAYMENTS[idx],
            }
        )

    names = [stage["name"].strip() or DEFAULT_STAGE_NAMES[i] for i, stage in enumerate(base)]
    durations = _normalize_sum([stage["duration_working_days"] for stage in base], target=110, min_each=1)
    payments = _normalize_sum([stage["payment_percent"] for stage in base], target=100, min_each=1)

    return [
        {
            "name": names[i],
            "duration_working_days": durations[i],
            "payment_percent": payments[i],
        }
        for i in range(3)
    ]


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    normalized["stages"] = _normalize_stages(payload["stages"])
    normalized["stages_count"] = 3
    normalized["total_duration_working_days"] = 110

    prepayment = _to_int(payload.get("prepayment_percent"), 50)
    normalized["prepayment_percent"] = min(50, max(0, prepayment))

    normalized["ip_transfer_model"] = "exclusive_transfer"
    normalized["access_transfer_required"] = True

    penalty = payload.get("penalty_percent_per_day", 0.5)
    try:
        penalty_f = float(penalty)
    except (TypeError, ValueError):
        penalty_f = 0.5
    normalized["penalty_percent_per_day"] = min(0.5, max(0.1, penalty_f))

    normalized["penalty_cap_percent"] = 10

    warranty = _to_int(payload.get("warranty_claim_window_months"), 12)
    normalized["warranty_claim_window_months"] = min(24, max(1, warranty))

    return normalized


def _validate_business_logic(payload: dict[str, Any]) -> None:
    total_duration = payload["total_duration_working_days"]
    if not isinstance(total_duration, int) or total_duration <= 0:
        raise ValidationError("total_duration_working_days must be a positive integer.")

    if total_duration != 110:
        raise ValidationError("total_duration_working_days must match template value: 110.")

    stages_count = payload["stages_count"]
    stages = payload["stages"]
    if not isinstance(stages_count, int) or stages_count != len(stages):
        raise ValidationError("stages_count must equal number of stage objects.")
    if stages_count != 3:
        raise ValidationError("stages_count must match template value: 3.")

    stage_duration_sum = 0
    stage_percent_sum = 0
    for idx, stage in enumerate(stages, start=1):
        duration = stage["duration_working_days"]
        percent = stage["payment_percent"]

        if not isinstance(duration, int) or duration <= 0:
            raise ValidationError(f"Stage #{idx} duration_working_days must be a positive integer.")
        if not isinstance(percent, int) or not 1 <= percent <= 100:
            raise ValidationError(f"Stage #{idx} payment_percent must be integer in range 1..100.")

        stage_duration_sum += duration
        stage_percent_sum += percent

    if stage_duration_sum != total_duration:
        raise ValidationError("Sum of stage durations must equal total_duration_working_days.")
    if stage_percent_sum != 100:
        raise ValidationError("Sum of stage payment_percent values must equal 100.")

    prepayment = payload["prepayment_percent"]
    if not isinstance(prepayment, int) or prepayment < 0:
        raise ValidationError("prepayment_percent must be a non-negative integer.")
    if prepayment > 50:
        raise ValidationError("prepayment_percent cannot exceed 50.")

    if payload["ip_transfer_model"] != "exclusive_transfer":
        raise ValidationError("ip_transfer_model must be 'exclusive_transfer'.")

    if payload["access_transfer_required"] is not True:
        raise ValidationError("access_transfer_required must be true.")

    penalty_per_day = payload["penalty_percent_per_day"]
    if not isinstance(penalty_per_day, (float, int)):
        raise ValidationError("penalty_percent_per_day must be a number.")
    if not 0.1 <= float(penalty_per_day) <= 0.5:
        raise ValidationError("penalty_percent_per_day must be in range 0.1..0.5.")

    if payload["penalty_cap_percent"] != 10:
        raise ValidationError("penalty_cap_percent must be exactly 10.")

    warranty = payload["warranty_claim_window_months"]
    if not isinstance(warranty, int) or not 1 <= warranty <= 24:
        raise ValidationError("warranty_claim_window_months must be an integer in range 1..24.")
