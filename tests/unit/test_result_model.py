"""诊断结果模型的行为契约。"""

import json

import pytest
from pydantic import ValidationError

from agent_doctor.models.enums import Status
from agent_doctor.models.result import CheckResult


def test_status_has_exactly_four_values() -> None:
    assert {status.value for status in Status} == {"pass", "warn", "fail", "info"}


def test_minimal_result_uses_defaults() -> None:
    result = CheckResult(name="demo", status=Status.PASS, summary="一切正常")
    assert result.details == {}
    assert result.recommendation is None
    assert result.exit_code == 0


def test_fail_maps_to_exit_code_one() -> None:
    result = CheckResult(name="demo", status=Status.FAIL, summary="出问题了")
    assert result.exit_code == 1


@pytest.mark.parametrize("status", [Status.PASS, Status.WARN, Status.INFO])
def test_non_fail_statuses_keep_exit_code_zero(status: Status) -> None:
    assert CheckResult(name="demo", status=status, summary="ok").exit_code == 0


def test_details_accept_flat_scalars() -> None:
    result = CheckResult(
        name="demo",
        status=Status.INFO,
        summary="ok",
        details={"text": "x", "count": 3, "ratio": 0.5, "flag": True, "nothing": None},
    )
    assert result.details["count"] == 3
    assert result.details["flag"] is True


@pytest.mark.parametrize(
    "details",
    [
        {"nested": {"a": 1}},
        {"items": [1, 2]},
        {"tuple": (1, 2)},
    ],
)
def test_details_reject_nested_structures(details: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CheckResult(name="demo", status=Status.PASS, summary="ok", details=details)


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CheckResult(name="demo", status=Status.PASS, summary="ok", unexpected="nope")


def test_model_is_frozen() -> None:
    result = CheckResult(name="demo", status=Status.PASS, summary="ok")
    with pytest.raises(ValidationError):
        result.name = "changed"


def test_blank_summary_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CheckResult(name="demo", status=Status.PASS, summary="   ")


def test_json_serialization_keeps_unicode() -> None:
    result = CheckResult(name="demo", status=Status.WARN, summary="中文说明", details={"n": 2})
    payload = json.loads(result.model_dump_json())
    assert payload["status"] == "warn"
    assert payload["summary"] == "中文说明"
    assert payload["details"] == {"n": 2}
    assert payload["recommendation"] is None
