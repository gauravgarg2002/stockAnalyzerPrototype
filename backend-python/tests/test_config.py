from pathlib import Path

import yaml

from app import config

ROOT = Path(__file__).resolve().parent.parent.parent


def test_defaults_equal_example_yaml():
    example = yaml.safe_load((ROOT / "config" / "app-config.example.yaml").read_text(encoding="utf-8"))
    assert config.DEFAULTS == example


def test_missing_file_gives_defaults_copy():
    cfg = config.load("/definitely/not/here.yaml")
    assert cfg == config.DEFAULTS and cfg is not config.DEFAULTS
    cfg["ports"]["python"] = 1
    assert config.DEFAULTS["ports"]["python"] == 8000


def test_deep_merge_over_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("adapters:\n  broker: kite_mcp\nllm:\n  provider: anthropic\n", encoding="utf-8")
    cfg = config.load(p)
    assert cfg["adapters"]["broker"] == "kite_mcp" and cfg["adapters"]["fundamentals"] == "mock"
    assert cfg["llm"]["provider"] == "anthropic" and cfg["llm"]["timeoutSeconds"] == 20


def test_env_app_config(tmp_path, monkeypatch):
    p = tmp_path / "env.yaml"
    p.write_text("ports:\n  python: 9999\n", encoding="utf-8")
    monkeypatch.setenv("APP_CONFIG", str(p))
    assert config.load()["ports"]["python"] == 9999
    monkeypatch.setenv("HOST", "0.0.0.0")
    assert config.host() == "0.0.0.0"


def test_broken_or_empty_yaml_is_ignored(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("a: [unclosed", encoding="utf-8")
    assert config.load(p) == config.DEFAULTS
    p.write_text("", encoding="utf-8")
    assert config.load(p) == config.DEFAULTS


def test_defaults_are_all_mock_and_no_secrets():
    a = config.DEFAULTS["adapters"]
    assert all(v == "mock" for k, v in a.items() if k not in ("prices", "statement") or v == "mock") and a["statement"] == "auto"
    assert config.DEFAULTS["kite"]["apiKey"] == "" and config.DEFAULTS["kite"]["apiSecret"] == "" and config.DEFAULTS["llm"]["apiKey"] == ""
    assert config.DEFAULTS["llm"]["provider"] == "none" and config.DEFAULTS["screener"]["sessionCookie"] == ""


def test_asof_mock_uses_sample_date_and_live_uses_real(tmp_path):
    from app import asof
    assert asof.today(config.DEFAULTS).isoformat() == "2026-10-30"
    live = {**config.DEFAULTS, "adapters": {k: ("amfi" if k == "fundMeta" else v) for k, v in config.DEFAULTS["adapters"].items()}}
    assert asof.today(config.DEFAULTS).isoformat() == "2026-10-30"
    allLive = {"adapters": {"broker": "kite_mcp", "fundamentals": "screener", "prices": "nse_eod", "surveillance": "nse", "fundNav": "mfapi", "fundMeta": "amfi",
                            "fundHoldings": "mfdata", "statement": "auto"}, "app": config.DEFAULTS["app"]}
    assert asof.today(allLive).isoformat() != "2026-10-30"
