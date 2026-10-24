"""脱敏规则：路径占位符、凭据模式、幂等性。"""

from pathlib import Path

import pytest

from agent_doctor.security.redact import redact, redact_paths, redact_secrets, redact_value

ROOTS: tuple[tuple[Path, str], ...] = (
    (Path("C:/Users/alice"), "<HOME>"),
    (Path("C:/Users/alice/AppData/Local/Temp"), "<TEMP>"),
    (Path("C:/Users/alice/proj"), "<CWD>"),
)


def test_home_path_is_replaced() -> None:
    text = r"C:\Users\alice\Documents\a.txt"
    assert redact_paths(text, roots=ROOTS) == r"<HOME>\Documents\a.txt"


def test_temp_path_wins_over_home() -> None:
    text = r"C:\Users\alice\AppData\Local\Temp\tmp123\x.log"
    assert redact_paths(text, roots=ROOTS) == r"<TEMP>\tmp123\x.log"


def test_cwd_wins_over_home() -> None:
    text = r"C:\Users\alice\proj\src\a.py"
    assert redact_paths(text, roots=ROOTS) == r"<CWD>\src\a.py"


def test_prefix_is_not_replaced_partially() -> None:
    text = r"C:\Users\alice2\Documents\a.txt"
    assert redact_paths(text, roots=ROOTS) == text


def test_path_outside_known_roots_is_untouched() -> None:
    text = r"D:\work\a.txt"
    assert redact_paths(text, roots=ROOTS) == text


def test_forward_slash_variant_is_replaced() -> None:
    assert redact_paths("C:/Users/alice/a.txt", roots=ROOTS) == "<HOME>/a.txt"


def test_openai_key() -> None:
    out = redact_secrets("key sk-abcdefghijklmnop1234 end")
    assert "sk-abcdefghijklmnop1234" not in out
    assert "<REDACTED:OPENAI_KEY>" in out


def test_github_token() -> None:
    out = redact_secrets("token=ghp_" + "a" * 20)
    assert "<REDACTED:GH_TOKEN>" in out


def test_aws_access_key() -> None:
    out = redact_secrets("AKIAIOSFODNN7EXAMPLE")
    assert "<REDACTED:AWS_KEY>" in out
    assert "AKIAIOSFODNN7EXAMPLE" not in out


def test_bearer_token() -> None:
    out = redact_secrets("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload")
    assert "eyJhbGciOiJIUzI1NiJ9" not in out
    assert "Bearer <REDACTED>" in out


def test_generic_key_value_pair() -> None:
    out = redact_secrets("API_KEY=super-secret-value")
    assert "super-secret-value" not in out
    assert "API_KEY=<REDACTED>" in out


def test_url_credentials_are_stripped() -> None:
    out = redact_secrets("http://user:hunter2@127.0.0.1:8080/")
    assert "hunter2" not in out
    assert out.startswith("http://<REDACTED>@")


@pytest.mark.parametrize(
    "text",
    [
        "端口 65532 连接成功（1.2 ms）",
        "SHA-256 与期望值一致",
        r"D:\work\build\agent-doctor.whl",
    ],
)
def test_plain_text_is_untouched(text: str) -> None:
    assert redact_secrets(text) == text


def test_redact_is_idempotent() -> None:
    text = r"C:\Users\alice\proj sk-abcdefghijklmnop API_KEY=xyz"
    once = redact(text, roots=ROOTS)
    assert redact(once, roots=ROOTS) == once


def test_redact_value_walks_nested_structures() -> None:
    payload = {
        "path": r"C:\Users\alice\proj\a.txt",
        "nested": {"token": "ghp_" + "b" * 20},
        "items": ["sk-abcdefghijklmnop", 1, None, True],
    }
    cleaned = redact_value(payload, roots=ROOTS)
    assert cleaned["path"] == r"<CWD>\a.txt"
    assert "ghp_" not in cleaned["nested"]["token"]
    assert cleaned["items"][0] == "<REDACTED:OPENAI_KEY>"
    assert cleaned["items"][1:] == [1, None, True]
