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


# Flexible ranges aligned with fuzzy LLM prompts.
TOTAL_DURATION_MIN_DAYS = 1
TOTAL_DURATION_MAX_DAYS = 1000
STAGES_MIN_COUNT = 1
STAGES_MAX_COUNT = 10
PREPAYMENT_MIN = 0
PREPAYMENT_MAX = 100
PENALTY_PER_DAY_MIN = 0.0
PENALTY_PER_DAY_MAX = 5.0
PENALTY_CAP_MIN = 0
PENALTY_CAP_MAX = 100
WARRANTY_MIN_MONTHS = 0
WARRANTY_MAX_MONTHS = 60
PAYMENT_SUM_TOLERANCE_PERCENT = 5


def parse_and_validate_project_json(raw_text: str) -> dict[str, Any]:
    """Parse LLM response text and validate flexible JSON constraints."""
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

    if not isinstance(payload["project_summary"], str):
        raise ValidationError("project_summary must be a string.")
    if not isinstance(payload["product_type"], str):
        raise ValidationError("product_type must be a string.")

    work_scope_items = payload["work_scope_items"]
    if not isinstance(work_scope_items, list) or not work_scope_items:
        raise ValidationError("work_scope_items must be a non-empty array.")
    if not all(isinstance(item, str) and item.strip() for item in work_scope_items):
        raise ValidationError("work_scope_items must contain non-empty strings.")

    stages = payload["stages"]
    if not isinstance(stages, list) or not stages:
        raise ValidationError("stages must be a non-empty array.")

    required_stage_keys = {"name", "duration_working_days", "payment_percent"}
    for idx, stage in enumerate(stages, start=1):
        if not isinstance(stage, dict):
            raise ValidationError(f"Stage #{idx} must be an object.")

        stage_keys = set(stage.keys())
        if stage_keys != required_stage_keys:
            raise ValidationError(
                f"Stage #{idx} must contain only {sorted(required_stage_keys)}"
            )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_business_logic(payload: dict[str, Any]) -> None:
    total_duration = payload["total_duration_working_days"]
    if not isinstance(total_duration, int):
        raise ValidationError("total_duration_working_days must be an integer.")
    if not TOTAL_DURATION_MIN_DAYS <= total_duration <= TOTAL_DURATION_MAX_DAYS:
        raise ValidationError(
            f"total_duration_working_days must be in range {TOTAL_DURATION_MIN_DAYS}..{TOTAL_DURATION_MAX_DAYS}."
        )

    stages_count = payload["stages_count"]
    stages = payload["stages"]
    if not isinstance(stages_count, int):
        raise ValidationError("stages_count must be an integer.")
    if not STAGES_MIN_COUNT <= stages_count <= STAGES_MAX_COUNT:
        raise ValidationError(
            f"stages_count must be in range {STAGES_MIN_COUNT}..{STAGES_MAX_COUNT}."
        )
    if stages_count != len(stages):
        raise ValidationError("stages_count must equal number of stage objects.")

    stage_duration_sum = 0
    stage_percent_sum = 0.0
    for idx, stage in enumerate(stages, start=1):
        name = stage["name"]
        duration = stage["duration_working_days"]
        percent = stage["payment_percent"]

        if not isinstance(name, str) or not name.strip():
            raise ValidationError(f"Stage #{idx} name must be a non-empty string.")
        if not isinstance(duration, int) or duration <= 0:
            raise ValidationError(f"Stage #{idx} duration_working_days must be a positive integer.")
        if not _is_number(percent) or not 0 < float(percent) <= 100:
            raise ValidationError(f"Stage #{idx} payment_percent must be in range 0..100.")

        stage_duration_sum += duration
        stage_percent_sum += float(percent)

    duration_delta = abs(stage_duration_sum - total_duration)
    allowed_delta = max(5, int(total_duration * 0.2))
    if duration_delta > allowed_delta:
        raise ValidationError(
            "Sum of stage durations is too far from total_duration_working_days "
            f"(delta={duration_delta}, allowed={allowed_delta})."
        )

    if abs(stage_percent_sum - 100.0) > PAYMENT_SUM_TOLERANCE_PERCENT:
        raise ValidationError(
            "Sum of stage payment_percent values must be close to 100 "
            f"(±{PAYMENT_SUM_TOLERANCE_PERCENT})."
        )

    prepayment = payload["prepayment_percent"]
    if not isinstance(prepayment, int):
        raise ValidationError("prepayment_percent must be an integer.")
    if not PREPAYMENT_MIN <= prepayment <= PREPAYMENT_MAX:
        raise ValidationError(
            f"prepayment_percent must be in range {PREPAYMENT_MIN}..{PREPAYMENT_MAX}."
        )

    ip_transfer_model = payload["ip_transfer_model"]
    if not isinstance(ip_transfer_model, str) or not ip_transfer_model.strip():
        raise ValidationError("ip_transfer_model must be a non-empty string.")

    if not isinstance(payload["access_transfer_required"], bool):
        raise ValidationError("access_transfer_required must be boolean.")

    penalty_per_day = payload["penalty_percent_per_day"]
    if not _is_number(penalty_per_day):
        raise ValidationError("penalty_percent_per_day must be a number.")
    if not PENALTY_PER_DAY_MIN <= float(penalty_per_day) <= PENALTY_PER_DAY_MAX:
        raise ValidationError(
            f"penalty_percent_per_day must be in range {PENALTY_PER_DAY_MIN}..{PENALTY_PER_DAY_MAX}."
        )

    penalty_cap_percent = payload["penalty_cap_percent"]
    if not isinstance(penalty_cap_percent, int):
        raise ValidationError("penalty_cap_percent must be an integer.")
    if not PENALTY_CAP_MIN <= penalty_cap_percent <= PENALTY_CAP_MAX:
        raise ValidationError(
            f"penalty_cap_percent must be in range {PENALTY_CAP_MIN}..{PENALTY_CAP_MAX}."
        )

    warranty = payload["warranty_claim_window_months"]
    if not isinstance(warranty, int):
        raise ValidationError("warranty_claim_window_months must be an integer.")
    if not WARRANTY_MIN_MONTHS <= warranty <= WARRANTY_MAX_MONTHS:
        raise ValidationError(
            "warranty_claim_window_months must be in range "
            f"{WARRANTY_MIN_MONTHS}..{WARRANTY_MAX_MONTHS}."
        )
