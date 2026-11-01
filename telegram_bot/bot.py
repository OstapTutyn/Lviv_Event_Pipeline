import os

import psycopg2
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from formatting import format_event_message

EVENTS_BUTTON_TEXT = "📅 Всі події"


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
    keyboard = [[KeyboardButton(EVENTS_BUTTON_TEXT)]]

    await update.message.reply_text(
        "Привіт! Я повідомлятиму про нові IT-події у Львові.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
        ),
    )


async def all_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        format_events(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^📅 Всі події$"),
            all_events,
        )
    )

    application.run_polling()


if __name__ == "__main__":
    main()