import importlib.util
import ast
from datetime import date
from pathlib import Path


FORMATTING_PATH = Path(__file__).parents[1] / "telegram_bot" / "formatting.py"
SPEC = importlib.util.spec_from_file_location("formatting", FORMATTING_PATH)
formatting = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(formatting)


def test_format_event_message_groups_events_by_ukrainian_date():
    message = formatting.format_event_message(
        [
            ("Перша подія", date(2026, 11, 12), "https://example.test/1"),
            ("Друга подія", date(2026, 11, 12), "https://example.test/2"),
            ("Третя подія", date(2026, 12, 1), "https://example.test/3"),
        ]
    )

    assert message.count("12 листопада 2026") == 1
    assert message.count("1 грудня 2026") == 1
    assert message.index("12 листопада 2026") < message.index("1 грудня 2026")
    assert message.count("Деталі") == 3


def test_format_event_message_escapes_html_in_title_and_link():
    message = formatting.format_event_message(
        [
            (
                "<script>alert(1)</script>",
                date(2026, 11, 12),
                "https://example.test/?a=1&b=2",
            )
        ]
    )

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in message
    assert 'a=1&amp;b=2' in message


def test_format_event_message_handles_empty_result():
    assert formatting.format_event_message([]) == "Наразі актуальних майбутніх подій немає."


def test_bot_uses_reply_keyboard_for_all_events():
    bot_source = (
        Path(__file__).parents[1] / "telegram_bot" / "bot.py"
    ).read_text()
    tree = ast.parse(bot_source)
    imported_names = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "telegram"
        for alias in node.names
    }

    assert {"KeyboardButton", "ReplyKeyboardMarkup"} <= imported_names
    assert "InlineKeyboardMarkup" not in bot_source
    assert "CallbackQueryHandler" not in bot_source
    assert 'EVENTS_BUTTON_TEXT = "📅 Всі події"' in bot_source
    assert "MessageHandler(" in bot_source
