"""``agent-doctor hash`` 的端到端行为。"""

import json
from pathlib import Path

ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    target = tmp_path / name
    target.write_bytes(data)
    return target


def test_hash_success_prints_digest(run_cli, tmp_path) -> None:
    target = _write(tmp_path, "abc.txt", b"abc")
    outcome = run_cli("hash", str(target))
    assert outcome.exit_code == 0
    assert ABC_SHA256 in outcome.text


def test_hash_json_output(run_cli, tmp_path) -> None:
    target = _write(tmp_path, "abc.txt", b"abc")
    outcome = run_cli("hash", str(target), "--json")
    assert outcome.exit_code == 0

    payload = json.loads(outcome.stdout)
    assert payload["name"] == "file.hash"
    assert payload["status"] == "pass"
    assert payload["details"]["sha256"] == ABC_SHA256
    assert payload["details"]["size_bytes"] == 3
    # tmp_path 位于系统临时目录下，JSON 输出里应当已被替换成 <TEMP> 占位符
    assert payload["details"]["path"].endswith("abc.txt")
    assert payload["details"]["path"].startswith("<")


def test_hash_empty_file(run_cli, tmp_path) -> None:
    target = _write(tmp_path, "empty.bin", b"")
    outcome = run_cli("hash", str(target), "--json")
    assert outcome.exit_code == 0
    assert json.loads(outcome.stdout)["details"]["sha256"] == EMPTY_SHA256


def test_hash_expected_match(run_cli, tmp_path) -> None:
    target = _write(tmp_path, "abc.txt", b"abc")
    outcome = run_cli("hash", str(target), "--expected", ABC_SHA256)
    assert outcome.exit_code == 0
    assert "一致" in outcome.text


def test_hash_expected_match_with_prefix(run_cli, tmp_path) -> None:
    target = _write(tmp_path, "abc.txt", b"abc")
    outcome = run_cli("hash", str(target), "--expected", f"sha256:{ABC_SHA256.upper()}")
    assert outcome.exit_code == 0


def test_hash_expected_mismatch_returns_one(run_cli, tmp_path) -> None:
    target = _write(tmp_path, "abc.txt", b"abc")
    wrong = "0" * 64
    outcome = run_cli("hash", str(target), "--expected", wrong, "--json")
    assert outcome.exit_code == 1

    payload = json.loads(outcome.stdout)
    assert payload["status"] == "fail"
    assert payload["details"]["expected"] == wrong
    assert payload["details"]["sha256"] == ABC_SHA256
    assert payload["recommendation"]


def test_hash_expected_invalid_format_returns_two(run_cli, tmp_path) -> None:
    target = _write(tmp_path, "abc.txt", b"abc")
    outcome = run_cli("hash", str(target), "--expected", "not-a-hash")
    assert outcome.exit_code == 2
    assert "64 位十六进制" in outcome.text
    assert "Traceback" not in outcome.text


def test_hash_missing_file_returns_two(run_cli, tmp_path) -> None:
    outcome = run_cli("hash", str(tmp_path / "missing.bin"))
    assert outcome.exit_code == 2
    assert "不存在" in outcome.text
    assert "Traceback" not in outcome.text


def test_hash_directory_returns_two(run_cli, tmp_path) -> None:
    outcome = run_cli("hash", str(tmp_path))
    assert outcome.exit_code == 2
    assert "目录" in outcome.text
    assert "Traceback" not in outcome.text
