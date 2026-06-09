"""Patch Hermes Telegram gateway to let finance inline buttons edit in place.

Hermes v2026.5.16 handles only built-in callback_data prefixes in
TelegramPlatform._handle_callback_query. Unknown callback data is returned
without query.answer(), so custom inline buttons spin forever.

Our /finance command sends the finance_api inline keyboard from the Hermes bot,
therefore those callbacks must be handled by the Hermes gateway process itself.
This patch adds a small finance-specific bridge that calls finance_api's
/bot/ui endpoints and edits the original Telegram message.
"""

from __future__ import annotations

from pathlib import Path

TARGET = Path("/opt/hermes-agent/gateway/platforms/telegram.py")
MARKER = "# --- Finance UI callbacks (sova-space patch) ---"
ANCHOR = "        # --- Update prompt callbacks ---\n"

PATCH = r'''        # --- Finance UI callbacks (sova-space patch) ---
        if data in {"balance_cb", "income", "spending", "subs", "skipped", "sync"} or data.startswith("spd:"):
            caller_id = str(getattr(query.from_user, "id", ""))
            if not self._is_callback_user_authorized(
                caller_id,
                chat_id=query_chat_id,
                chat_type=str(query_chat_type) if query_chat_type is not None else None,
                thread_id=str(query_thread_id) if query_thread_id is not None else None,
                user_name=query_user_name,
            ):
                await query.answer(text="⛔ You are not authorized to use finance buttons.")
                return

            await query.answer()
            try:
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
                logger.error("[%s] finance callback failed: %s", self.name, exc, exc_info=True)
                try:
                    await query.answer(text="Finance UI failed.")
                except Exception:
                    pass
            return

'''


def main() -> None:
    text = TARGET.read_text()
    if MARKER in text:
        print("finance callback patch already applied")
        return
    if ANCHOR not in text:
        raise SystemExit(f"anchor not found in {TARGET}")
    TARGET.write_text(text.replace(ANCHOR, PATCH + ANCHOR, 1))
    print("applied finance callback patch")


if __name__ == "__main__":
    main()
