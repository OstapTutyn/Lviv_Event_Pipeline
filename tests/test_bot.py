import importlib.util
from datetime import date
from pathlib import Path


FORMATTING_PATH = Path(__file__).parents[1] / "telegram_bot" / "formatting.py"
SPEC = importlib.util.spec_from_file_location("formatting", FORMATTING_PATH)
formatting = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(formatting)


def test_format_event_message_escapes_html():
    message = formatting.format_event_message(
        [("<script>alert(1)</script>", date(2026, 11, 12), "https://example.test/?a=1&b=2")]
    )

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in message
    assert 'a=1&amp;b=2' in message


def test_format_event_message_handles_empty_result():
    assert formatting.format_event_message([]) == "Наразі актуальних майбутніх подій немає."
