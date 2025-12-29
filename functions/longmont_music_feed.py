import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

print("Function loaded")

def handler(event, context):
    URL = "https://www.downtownlongmont.com/events/calendar"

    MUSIC_KEYWORDS = [
        "band", "live music", "concert", "jazz", "acoustic", "set",
        "performance", "singer", "songwriter", "dj", "bluegrass", "punk", "rock", "metal", "R&B", "soul", "hip-hop", "rap", "electronic"
    ]

    EXCLUDE_KEYWORDS = [
        "open mic", "karaoke", "trivia", "comedy", "workshop"
    ]

    def is_music_event(text):
        t = text.lower()
        return (
            any(k in t for k in MUSIC_KEYWORDS)
            and not any(k in t for k in EXCLUDE_KEYWORDS)
        )

    def parse_time_range(time_str):
        match = re.match(
            r"(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m)",
            time_str.lower()
        )
        if not match:
            return None, None
        start_raw, end_raw = match.groups()
        fmt = "%I%p" if ":" not in start_raw else "%I:%M%p"
        start = datetime.strptime(start_raw, fmt)
        end = datetime.strptime(end_raw, fmt)
        return start, end

    tz = pytz.timezone("America/Denver")
    now = datetime.now(tz)

    html = requests.get(URL).text
    soup = BeautifulSoup(html, "html.parser")

    events = []

    for item in soup.find_all(True):
        text = item.get_text(" ", strip=True)
        if not is_music_event(text):
            continue

        title_el = item.find(["h3", "h2"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        date_match = re.search(r"([A-Za-z]{3,9}\s+\d{1,2})", text)
        if not date_match:
            continue
        date_str = date_match.group(1)
        date = datetime.strptime(date_str + " 2025", "%b %d %Y")

        time_match = re.search(
            r"\d{1,2}(:\d{2})?\s*[ap]m\s*-\s*\d{1,2}(:\d{2})?\s*[ap]m",
            text.lower()
        )
        if not time_match:
            continue

        start_t, end_t = parse_time_range(time_match.group(0))
        if not start_t:
            continue

        start_dt = tz.localize(datetime.combine(date.date(), start_t.time()))
        end_dt = tz.localize(datetime.combine(date.date(), end_t.time()))

        if end_dt < now:
            continue

        location = "Downtown Longmont"

        events.append({
            "title": title,
            "start": start_dt,
            "end": end_dt,
            "location": location
        })

    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Longmont Live Music Feed//EN"
    ]

    for event in events:
        ics.append("BEGIN:VEVENT")
        ics.append(f"SUMMARY:{event['title']}")
        ics.append(f"LOCATION:{event['location']}")
        ics.append(f"DTSTART:{event['start'].strftime('%Y%m%dT%H%M%S')}")
        ics.append(f"DTEND:{event['end'].strftime('%Y%m%dT%H%M%S')}")
        ics.append("END:VEVENT")

    ics.append("END:VCALENDAR")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/calendar",
            "Cache-Control": "max-age=3600"
        },
        "body": "\n".join(ics)
    }
