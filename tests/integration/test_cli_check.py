"""``agent-doctor check`` 的端到端行为。"""

import json

BUILTIN_CHECKS = {"python.version", "platform.info", "path.health", "toolchain.presence"}


def test_check_runs_all_builtin_checks(run_cli) -> None:
    outcome = run_cli("check")
    assert outcome.exit_code == 0
    for name in BUILTIN_CHECKS:
        assert name in outcome.text


def test_check_json_report(run_cli) -> None:
    outcome = run_cli("check", "--json")
    assert outcome.exit_code == 0

    payload = json.loads(outcome.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["tool"]["name"] == "agent-doctor"
    assert payload["summary"]["total"] == len(payload["results"])

    names = {item["name"] for item in payload["results"]}
    assert names >= BUILTIN_CHECKS

    for item in payload["results"]:
        assert item["status"] in {"pass", "warn", "fail", "info"}
        assert {"name", "status", "summary", "details"} <= set(item)


def test_check_only_filters(run_cli) -> None:
    outcome = run_cli("check", "--only", "python.version", "--json")
    assert outcome.exit_code == 0

    payload = json.loads(outcome.stdout)
    assert len(payload["results"]) == 1
    assert payload["results"][0]["name"] == "python.version"


def test_check_unknown_only_returns_two(run_cli) -> None:
    outcome = run_cli("check", "--only", "does.not.exist")
    assert outcome.exit_code == 2
    assert "未知的检查项" in outcome.text
    assert "Traceback" not in outcome.text
