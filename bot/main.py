from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import LinkPreviewOptions, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from bot.db import Database
from bot.recipes import RecipeClient
from bot.service import GroceryService
from bot.textutil import split_telegram

ROOT = Path(__file__).resolve().parent.parent
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
log = logging.getLogger("bot")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(ROOT / ".env")
    token = _required("TELEGRAM_BOT_TOKEN")
    code = _required("HOUSEHOLD_CODE")
    database_path = Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "lista.db")))
    if not database_path.is_absolute():
        database_path = ROOT / database_path
    service = GroceryService(Database(database_path), RecipeClient(), code)
    app = Application.builder().token(token).build()
    app.bot_data["service"] = service
    app.add_handler(MessageHandler(filters.TEXT, on_text))
    log.info("Bot escuchando. La lista está en %s", database_path)
    app.run_polling(drop_pending_updates=True)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = update.effective_user
    if message is None or not message.text or user is None:
        return
    service: GroceryService = context.application.bot_data["service"]
    reply = await service.reply(user.id, user.first_name or "alguien", message.text)
    for part in split_telegram(reply):
        await message.reply_text(part, link_preview_options=NO_PREVIEW)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Falta {name} en el archivo .env")
    return value


if __name__ == "__main__":
    main()
