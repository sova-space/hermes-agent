"""Callback chat extraction for agent-silence plugin."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "hermes/plugins/agent-silence"
PACKAGE_NAME = "agent_silence_callback_test"


def load_plugin_module(name: str):
    import types

    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(PLUGIN_DIR)]
        sys.modules[PACKAGE_NAME] = package

    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    spec = importlib.util.spec_from_file_location(full_name, PLUGIN_DIR / f"{name}.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_callback_chat_context_falls_back_to_callback_message_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    plugin = load_plugin_module("__init__")
    event = SimpleNamespace(
        source=SimpleNamespace(chat_id=None, thread_id=None),
        callback_query=SimpleNamespace(
            message=SimpleNamespace(
                chat=SimpleNamespace(id=-100123),
                message_thread_id=777,
            )
        ),
    )

    chat = plugin._chat_context(event)

    assert chat.chat_id == "-100123"
    assert chat.thread_id == "777"
