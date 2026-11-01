import os

import psycopg2
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from formatting import format_event_message


def get_connection():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
    )


def format_events():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT title, event_date, link
                FROM public.active_events
                ORDER BY event_date, id
                """
            )
            events = cursor.fetchall()

    return format_event_message(events)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Всі події", callback_data="all_events")]
    ]

    await update.message.reply_text(
        "Привіт! Я повідомлятиму про нові IT-події у Львові.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def all_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        format_events(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(all_events, pattern="^all_events$")
    )

    application.run_polling()


if __name__ == "__main__":
    main()