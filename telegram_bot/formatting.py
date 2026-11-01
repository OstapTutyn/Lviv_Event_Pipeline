from html import escape


def format_event_message(events):
    if not events:
        return "Наразі актуальних майбутніх подій немає."

    messages = ["📅 Актуальні події у Львові:\n"]

    for index, (title, event_date, link) in enumerate(events, start=1):
        messages.append(
            f"{index}. <b>{escape(str(title))}</b>\n"
            f"📅 {event_date.strftime('%d.%m.%Y')}\n"
            f'🔗 <a href="{escape(str(link), quote=True)}">Деталі</a>\n'
        )

    return "\n".join(messages)
