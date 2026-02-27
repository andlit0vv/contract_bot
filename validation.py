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


def parse_and_validate_project_json(raw_text: str) -> dict[str, Any]:
    """Parse LLM response text and validate JSON structure and business logic."""
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"LLM response is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValidationError("Top-level JSON must be an object.")

    _validate_structure(payload)
    _validate_business_logic(payload)
    return payload


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

