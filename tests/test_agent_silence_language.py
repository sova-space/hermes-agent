"""General language selector for the Hermes profile router."""

import importlib.util
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "hermes/plugins/agent-silence"
PACKAGE_NAME = "agent_silence_test"


def load_plugin_module(name: str):
    if PACKAGE_NAME not in sys.modules:
        import types

        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(PLUGIN_DIR)]
        sys.modules[PACKAGE_NAME] = package

    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    spec = importlib.util.spec_from_file_location(full_name, PLUGIN_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_doer_session_persists_general_language(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    doer = load_plugin_module("doer")

    session = doer.DoerSession()
    assert session.active_language("chat-1") == "en"

    session.set_language("chat-1", "uk")

    reloaded = doer.DoerSession()
    assert reloaded.active_language("chat-1") == "uk"


def test_language_payload_is_general_and_marks_current(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    commands = load_plugin_module("commands")
    session = commands.DoerSession()
    session.set_language("chat-1", "uk")

    payload = commands._language_payload("chat-1", session)

    assert payload["text"] == "<b>Language</b>"
    rows = payload["reply_markup"]["inline_keyboard"]
    assert rows[0][0]["text"] == "English"
    assert rows[0][1]["text"] == "✅ Українська"
    assert rows[0][1]["callback_data"] == "lang:uk"
