import json

from trader.config import Config


def test_load_secrets_only_applies_whitelisted_secret_keys(tmp_path, monkeypatch, caplog):
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(
        json.dumps(
            {
                "api_key": "real-key",
                "api_secret": "real-secret",
                "telegram_bot_token": "real-token",
                "telegram_chat_id": "12345",
                "strategy_runtime_enabled": False,
                "enabled_strategies": [],
                "strategy_runtime_side_filter": "short",
                "unknown_runtime_key": "ignored",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(Config, "API_KEY", "default-key")
    monkeypatch.setattr(Config, "API_SECRET", "default-secret")
    monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(Config, "TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(Config, "STRATEGY_RUNTIME_ENABLED", True)
    monkeypatch.setattr(Config, "ENABLED_STRATEGIES", ["fixture"])
    monkeypatch.setattr(Config, "STRATEGY_RUNTIME_SIDE_FILTER", "both")

    Config.load_secrets(str(secrets_path))

    assert Config.API_KEY == "real-key"
    assert Config.API_SECRET == "real-secret"
    assert Config.TELEGRAM_BOT_TOKEN == "real-token"
    assert Config.TELEGRAM_CHAT_ID == "12345"
    assert Config.STRATEGY_RUNTIME_ENABLED is True
    assert Config.ENABLED_STRATEGIES == ["fixture"]
    assert Config.STRATEGY_RUNTIME_SIDE_FILTER == "both"
    assert "Ignored non-secret key(s) in secrets file" in caplog.text
