"""Patch Hermes Telegram gateway for custom Sova inline callbacks.

Hermes v2026.5.16 handles only built-in callback_data prefixes in
TelegramPlatform._handle_callback_query. Unknown callback data is returned
without query.answer(), so custom inline buttons spin forever.

Sova's /finance and /profile commands are sent by the Hermes bot and must edit
one main Telegram message in place. This build-time patch handles those custom
callback prefixes directly inside the Telegram gateway process.
"""

from __future__ import annotations

from pathlib import Path

TARGET = Path("/opt/hermes-agent/gateway/platforms/telegram.py")
MARKER = "# --- Sova custom inline callbacks (sova-space patch) ---"
ANCHOR = "        # --- Update prompt callbacks ---\n"

PATCH = r"""        # --- Sova custom inline callbacks (sova-space patch) ---
        if data in {"balance_cb", "income", "spending", "month", "subs", "skipped", "sync"} or data.startswith(("spd:", "month:", "prof:project:", "prof:mode:", "lang:")):
            caller_id = str(getattr(query.from_user, "id", ""))
            if not self._is_callback_user_authorized(
                caller_id,
                chat_id=query_chat_id,
                chat_type=str(query_chat_type) if query_chat_type is not None else None,
                thread_id=str(query_thread_id) if query_thread_id is not None else None,
                user_name=query_user_name,
            ):
                await query.answer(text="⛔ You are not authorized to use this button.")
                return

            await query.answer()
            try:
                import json
                from pathlib import Path as _Path

                chat_id = str(query_chat_id) if query_chat_id is not None else ""
                state_path = _Path(os.environ.get("HERMES_HOME", "/data/.hermes")) / "agent-silence-session.json"
                try:
                    state = json.loads(state_path.read_text())
                except Exception:
                    state = {}

                if data.startswith("lang:"):
                    languages = {"en": "English", "uk": "Українська"}
                    language = data.split(":", 1)[1]
                    if language not in languages:
                        await query.answer(text="Unknown language.")
                        return
                    if not chat_id:
                        await query.answer(text="Chat missing.")
                        return

                    active_language = state.get("active_language") if isinstance(state.get("active_language"), dict) else {}
                    active_language[chat_id] = language
                    state["active_language"] = active_language
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = state_path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(state, sort_keys=True))
                    tmp.replace(state_path)

                    try:
                        import httpx

                        with httpx.Client(timeout=5) as client:
                            for key, value in os.environ.items():
                                if key.startswith("AGENT_") and key.endswith("_URL"):
                                    base = value.rstrip("/")
                                    if base and not base.startswith("http"):
                                        base = f"https://{base}"
                                    if base:
                                        client.put(f"{base}/bot/language", json={"language": language})
                    except Exception:
                        pass

                    rows = [[
                        InlineKeyboardButton(
                            f"{'✅ ' if language == code else ''}{name}",
                            callback_data=f"lang:{code}",
                        )
                        for code, name in languages.items()
                    ]]
                    await query.edit_message_text(
                        text="<b>Language</b>",
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(rows),
                    )
                    return

                if data.startswith(("prof:project:", "prof:mode:")):
                    projects = ["finance", "hermes", "wishlist"]
                    if not chat_id:
                        await query.answer(text="Chat missing.")
                        return

                    state_path = _Path(os.environ.get("HERMES_HOME", "/data/.hermes")) / "agent-silence-session.json"
                    try:
                        state = json.loads(state_path.read_text())
                    except Exception:
                        state = {}
                    active_profile = state.get("active_profile") if isinstance(state.get("active_profile"), dict) else {}
                    active_mode = state.get("active_mode") if isinstance(state.get("active_mode"), dict) else {}

                    profile = str(active_profile.get(chat_id) or projects[0])
                    mode = str(active_mode.get(chat_id) or "client")
                    if data.startswith("prof:project:"):
                        profile = data.split(":", 2)[2]
                    else:
                        mode = data.split(":", 2)[2]
                    if profile not in projects or mode not in {"client", "dev"}:
                        await query.answer(text="Unknown profile or mode.")
                        return

                    active_profile[chat_id] = profile
                    active_mode[chat_id] = mode
                    state["active_profile"] = active_profile
                    state["active_mode"] = active_mode
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = state_path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(state, sort_keys=True))
                    tmp.replace(state_path)

                    rows = [
                        [
                            InlineKeyboardButton(
                                f"{'✅ ' if profile == project else ''}{project}",
                                callback_data=f"prof:project:{project}",
                            )
                            for project in projects
                        ],
                        [
                            InlineKeyboardButton(
                                f"{'✅ ' if mode == 'client' else ''}💬 client",
                                callback_data="prof:mode:client",
                            ),
                            InlineKeyboardButton(
                                f"{'✅ ' if mode == 'dev' else ''}🔧 dev",
                                callback_data="prof:mode:dev",
                            ),
                        ],
                    ]
                    text = (
                        "<b>Project router</b>\n"
                        f"<b>Active:</b> <code>{profile}</code> · <b>{mode}</b>"
                    )
                    await query.edit_message_text(
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(rows),
                    )
                    return

                import httpx
                from urllib.parse import quote

                base_url = (
                    os.environ.get("AGENT_FINANCE_URL")
                    or os.environ.get("FINANCE_API_URL", "")
                ).rstrip("/")
                if base_url and not base_url.startswith("http"):
                    base_url = f"https://{base_url}"
                if not base_url:
                    await query.answer(text="Finance API URL missing.")
                    return

                view_map = {
                    "balance_cb": "balance",
                    "income": "income",
                    "spending": "spending",
                    "month": "month",
                    "subs": "subs",
                    "skipped": "skipped",
                }
                method = "GET"
                if data == "sync":
                    method = "POST"
                    path = "/bot/ui/finance/sync"
                elif data.startswith("spd:"):
                    category = data[len("spd:"):]
                    path = f"/bot/ui/finance/spending/{quote(category, safe='')}"
                elif data.startswith("month:"):
                    path = f"/bot/ui/finance/{data}"
                else:
                    path = f"/bot/ui/finance/{view_map[data]}"

                with httpx.Client(timeout=10) as client:
                    resp = client.post(f"{base_url}{path}") if method == "POST" else client.get(f"{base_url}{path}")
                    resp.raise_for_status()
                    payload = resp.json()

                await query.edit_message_text(
                    text=payload.get("text", ""),
                    parse_mode=payload.get("parse_mode", ParseMode.HTML),
                    reply_markup=payload.get("reply_markup"),
                )
            except Exception as exc:
                logger.error("[%s] custom inline callback failed: %s", self.name, exc, exc_info=True)
                try:
                    await query.answer(text="Button action failed.")
                except Exception:
                    pass
            return

"""


def main() -> None:
    text = TARGET.read_text()
    if MARKER in text:
        print("custom inline callback patch already applied")
        return
    old_marker = "# --- Finance UI callbacks (sova-space patch) ---"
    if old_marker in text:
        raise SystemExit(
            "old finance-only patch is already applied; rebuild from clean Hermes source"
        )
    if ANCHOR not in text:
        raise SystemExit(f"anchor not found in {TARGET}")
    TARGET.write_text(text.replace(ANCHOR, PATCH + ANCHOR, 1))
    print("applied custom inline callback patch")


if __name__ == "__main__":
    main()
