import hashlib
import json

from bs4 import BeautifulSoup


def parse_events(html):
    """Extract the stable event contract from a DOU calendar page."""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for card in soup.find_all("article", class_="b-postcard"):
        title_tag = card.select_one("h2.title a")
        if title_tag is None or not title_tag.get("href"):
            continue

        when_where_tag = card.find("div", class_="when-and-where")
        events.append(
            {
                "title": title_tag.get_text(strip=True),
                "date": (
                    when_where_tag.get_text(" ", strip=True)
                    if when_where_tag
                    else "Не вказано"
                ),
                "link": title_tag["href"],
            }
        )
    return events


def event_payload(event):
    return json.dumps(event, ensure_ascii=False, sort_keys=True)


def payload_hash(event):
    return hashlib.sha256(event_payload(event).encode("utf-8")).hexdigest()
