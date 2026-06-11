"""Hermes router finance month callback tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_hermes_plugin_routes_month_callback():
    text = (REPO_ROOT / "hermes/plugins/agent-silence/commands.py").read_text()

    assert '"month": "month"' in text
    assert "_FINANCE_MONTH_PREFIX" in text
    assert "_FINANCE_BALANCE_PREFIX" in text
    assert "_FINANCE_SUBS_PREFIX" in text
    assert 'data.startswith("spending:")' in text


def test_railway_gateway_patch_allows_month_callback():
    text = (REPO_ROOT / "infra/patch_telegram_finance_callbacks.py").read_text()

    assert '"month"' in text
    assert '"month": "month"' in text
    assert '"month:"' in text
    assert '"balance_cb:"' in text
    assert '"spending:"' in text
    assert '"subs:"' in text
