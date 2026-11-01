import importlib.util
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
