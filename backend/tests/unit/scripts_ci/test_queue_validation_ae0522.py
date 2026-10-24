"""The disposable-droplet validation tooling (``ops/queue-validation``).

Scenario: The validation droplet never holds production credentials
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[4]
TOOLS = REPO_ROOT / "ops" / "queue-validation"
OUTBOUND = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GLM_API_KEY",
    "GEMINI_API_KEY",
    "PINECONE_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE",
)


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _env_text() -> str:
    """The env file the template writes, with its random parts filled in.

    The template is a heredoc; ``$(rand ...)`` and the derived values are
    replaced by fixed text, so the test reads exactly the names and literal
    prefixes the droplet gets, without running a shell.
    """
    body = (TOOLS / "env_template.sh").read_text(encoding="utf-8")
    heredoc = body.split("<<ENV\n", 1)[1].split("\nENV\n", 1)[0]
    return re.sub(r"\$\([^)]*\)|\$\{[A-Z_]+\}", "generated0123456789", heredoc)


def test_the_template_holds_only_stubs_and_internal_endpoints() -> None:
    """Scenario: The validation droplet never holds production credentials"""
    check = _load("credential_check")
    values = check.env_values(_env_text())
    for name in OUTBOUND:
        assert values[name].startswith("stub-"), name
    assert values["GROKBOT_IMAGE_WEBHOOK_URL"] == "http://llm-mock:8080/grok"
    assert values["IMAGE_BRIDGE_FALLBACK_ENABLED"] == "false"
    assert values["META_IG_ACCESS_TOKEN"] == ""
    assert values["TELEGRAM_ALERTS_BOT_TOKEN"] == ""
    assert values["CAROUSEL_CHECKPOINT_BACKEND"] == "postgres"


def test_the_check_fires_on_a_production_value(tmp_path: Path) -> None:
    """Scenario: The validation droplet never holds production credentials"""
    check = _load("credential_check")
    secret = "prod-telegram-token-123456"
    hashes = tmp_path / "prod-hashes.txt"
    hashes.write_text(hashlib.sha256(secret.encode()).hexdigest() + "\n")
    clean = tmp_path / "clean.env"
    clean.write_text(_env_text())
    leaked = tmp_path / "leaked.env"
    leaked.write_text(_env_text() + f"\nTELEGRAM_BOT_TOKEN='{secret}'\nPORT=1\n")
    assert check.main([str(clean), str(hashes)]) == check.EXIT_CLEAN
    assert check.main([str(leaked), str(hashes)]) == check.EXIT_LEAK
    assert check.leaks(leaked.read_text(), {hashlib.sha256(b"1").hexdigest()}) == []
    empty = tmp_path / "empty.txt"
    empty.write_text("\n")
    assert check.main([str(clean), str(empty)]) == check.EXIT_USAGE
    assert check.main([str(clean)]) == check.EXIT_USAGE


def test_the_p95_verdict_uses_a_twenty_percent_budget(tmp_path: Path) -> None:
    """Scenario: The validation droplet never holds production credentials"""
    load = _load("load_p95")
    idle = tmp_path / "idle.samples"
    busy = tmp_path / "busy.samples"
    idle.write_text(
        "".join(json.dumps({"ms": 100.0, "ok": True}) + "\n" for _ in range(40))
    )
    busy.write_text(
        "".join(json.dumps({"ms": 119.0, "ok": True}) + "\n" for _ in range(40))
    )
    assert load.verdict(str(idle), str(busy))["within_budget"] is True
    with busy.open("a") as handle:
        handle.write(
            "".join(json.dumps({"ms": 900.0, "ok": False}) + "\n" for _ in range(10))
        )
    verdict = load.verdict(str(idle), str(busy))
    assert verdict["within_budget"] is False
    assert verdict["under_generation"]["errors"] == 10


def test_the_mock_answers_tools_and_schemas_with_valid_values() -> None:
    """Scenario: The validation droplet never holds production credentials"""
    mock = _load("mock_upstream")
    schema = {
        "type": "object",
        "properties": {
            "slides": {"type": "array", "items": {"type": "string"}, "minItems": 2},
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "kind": {"enum": ["a", "b"]},
        },
    }
    value = mock.synthesize(schema)
    assert value["kind"] == "a"
    assert value["score"] == 100
    assert len(value["slides"]) >= 2
    message, label = mock.chat_answer({
        "tools": [{"function": {"name": "emit", "parameters": schema}}],
        "messages": [],
    })
    assert label == "tool:emit"
    assert json.loads(message["tool_calls"][0]["function"]["arguments"])["kind"] == "a"
    assert mock.png(8).startswith(b"\x89PNG")


def test_the_driver_script_defines_its_inputs_before_using_them() -> None:
    """Scenario: The validation droplet never holds production credentials"""
    script = (TOOLS / "validate.sh").read_text(encoding="utf-8")
    main = script[script.index("main() {") :]
    assert script.index('SCOUT_KEY="$(openssl rand') < script.index("remote() {")
    assert main.index("provision") < main.index("remote prepare")
    assert main.index("lock_egress") < main.index("write_env") < main.index("remote up")
    assert main.index("remote deploy_cycle") < main.index("revert_rehearsal")
    assert "trap teardown EXIT" in script
    assert "trap 'exit 130' INT" in script
    assert "trap 'exit 143' TERM" in script
