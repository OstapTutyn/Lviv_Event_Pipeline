import importlib.util
from datetime import datetime, timezone
from pathlib import Path


UTILS_PATH = Path(__file__).parents[1] / "dags" / "event_utils.py"
SPEC = importlib.util.spec_from_file_location("event_utils", UTILS_PATH)
event_utils = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(event_utils)


def test_parse_events_extracts_normalized_event_contract():
    html = """
    <article class="b-postcard">
      <h2 class="title"><a href="https://dou.ua/event/1"> Event &amp; One </a></h2>
      <div class="when-and-where"> 12 листопада 18:00 </div>
    </article>
    """

    assert event_utils.parse_events(html) == [
        {
            "title": "Event & One",
            "date": "12 листопада 18:00",
            "link": "https://dou.ua/event/1",
        }
    ]


def test_parse_events_skips_cards_without_links():
    assert event_utils.parse_events(
        '<article class="b-postcard"><h2 class="title">No link</h2></article>'
    ) == []


def test_payload_hash_is_stable_for_key_order():
    first = {"title": "Подія", "date": "1 січня", "link": "https://example.test"}
    second = {"link": first["link"], "date": first["date"], "title": first["title"]}

    assert event_utils.payload_hash(first) == event_utils.payload_hash(second)


def test_select_new_event_candidates_includes_first_seen_unnotified_event():
    rows = [
        (
            "https://example.test/new",
            "Нова подія",
            "1 січня",
            "hash-new",
            datetime.now(timezone.utc),
            None,
        )
    ]

    assert event_utils.select_new_event_candidates(rows) == [rows[0][:4]]


def test_select_new_event_candidates_skips_unchanged_notified_event():
    rows = [
        (
            "https://example.test/unchanged",
            "Подія",
            "1 січня",
            "hash-same",
            datetime.now(timezone.utc),
            "https://example.test/unchanged",
        )
    ]

    assert event_utils.select_new_event_candidates(rows) == []


def test_select_new_event_candidates_skips_changed_existing_event():
    rows = [
        (
            "https://example.test/changed",
            "Оновлена подія",
            "2 січня",
            "hash-new-version",
            datetime.now(timezone.utc),
            "https://example.test/changed",
        )
    ]

    assert event_utils.select_new_event_candidates(rows) == []
