#!/usr/bin/env python3
"""
מעטפת ל-Google Calendar API דרך הרשאת OAuth אישית - רשימת יומנים, קריאת
אירועים בטווח תאריכים, יצירת אירוע ועדכון אירוע.

אין כאן פעולת מחיקה, במכוון. מחיקת אירוע היא פעולה הרסנית, ולכן היא נשארת
ידנית ביומן עצמו - בדיוק כמו ש-smoove-newsletter לא שולח בפועל ו-airtable-write
לא מעדכן. אם יידרש בעתיד לבטל אירוע, הדרך הנכונה היא update-event עם
--status cancelled, שהוא הפיך, ולא מחיקה.

הקמה חד-פעמית: ראו scripts/calendar_oauth_setup.py.

שימוש:
    python3 gcal.py list-calendars
    python3 gcal.py list-events --calendar "עבודה" --from 2026-08-10 --to 2026-08-17
    python3 gcal.py create-event --calendar "עבודה" --title "שיחה עם לקוח" \
        --start 2026-08-12T10:00 --end 2026-08-12T11:00 [--description "..."] [--location "..."]
    python3 gcal.py create-event --calendar "אישי" --title "חופש" --start 2026-08-20 --all-day
    python3 gcal.py update-event --calendar "עבודה" --event-id <id> --title "שם חדש"

--calendar מקבל מזהה יומן מלא, את המילה primary, או קטע משם היומן (למשל
"עבודה") - ההתאמה לפי שם נפתרת מול רשימת היומנים בפועל, ואם היא דו-משמעית
הסקריפט עוצר ומציג את המועמדים במקום לנחש.

דורש ב-.env:
    GOOGLE_CALENDAR_OAUTH_TOKEN_FILE - נתיב לקובץ הטוקן שנוצר ע"י calendar_oauth_setup.py
    GOOGLE_CALENDAR_ID (אופציונלי)   - יומן ברירת מחדל כש---calendar לא נמסר

דורש: pip3 install google-auth requests
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import AuthorizedSession
except ImportError:
    print(
        "חסרות חבילות. הריצו: pip3 install google-auth requests",
        file=sys.stderr,
    )
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]
BASE_URL = "https://www.googleapis.com/calendar/v3"
CALENDAR_LIST_URL = f"{BASE_URL}/users/me/calendarList"
DEFAULT_TIMEZONE = "Asia/Jerusalem"

DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$")


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False))
    sys.exit(1)


def get_session():
    token_file = os.environ.get("GOOGLE_CALENDAR_OAUTH_TOKEN_FILE")
    if not token_file or not os.path.isfile(token_file):
        fail(
            "GOOGLE_CALENDAR_OAUTH_TOKEN_FILE לא מוגדר או שהקובץ לא נמצא - "
            "הריצו קודם python3 calendar_oauth_setup.py"
        )
    with open(token_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    credentials = Credentials(
        token=None,
        refresh_token=data["refresh_token"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        scopes=SCOPES,
    )
    # AuthorizedSession מרענן את האסימון אוטומטית לפי הצורך - הוא לעולם לא נחשף החוצה.
    return AuthorizedSession(credentials)


def api(session, method, path, **kwargs):
    resp = session.request(method, f"{BASE_URL}{path}", timeout=30, **kwargs)
    if resp.status_code >= 400:
        # SERVICE_DISABLED מגיע כשה-API עצמו כבוי בפרויקט ה-Cloud - שגיאה שנראית
        # כמו בעיית הרשאות אבל הפתרון שלה שונה לגמרי, ולכן היא מוסברת במפורש.
        if "SERVICE_DISABLED" in resp.text:
            fail(
                "Google Calendar API כבוי בפרויקט ה-Google Cloud. הפעילו אותו ב-"
                "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com "
                "ונסו שוב בעוד דקה."
            )
        fail(f"קריאה ל-Calendar API נכשלה ({resp.status_code}): {resp.text}")
    return resp.json() if resp.content else {}


def fetch_calendars(session):
    calendars, page_token = [], None
    while True:
        params = {"maxResults": 250, "showHidden": True}
        if page_token:
            params["pageToken"] = page_token
        body = api(session, "GET", "/users/me/calendarList", params=params)
        calendars.extend(body.get("items", []))
        page_token = body.get("nextPageToken")
        if not page_token:
            break
    return calendars


def resolve_calendar(session, requested):
    """מזהה יומן מלא / primary / קטע משם -> מזהה יומן ודאי.

    התאמה לפי שם נעשית מול הרשימה האמיתית, ודו-משמעות עוצרת במקום לנחש -
    כתיבה ליומן הלא נכון היא בדיוק סוג הטעות שקשה לשים לב אליה אחר כך.
    """
    requested = requested or os.environ.get("GOOGLE_CALENDAR_ID") or "primary"
    if requested == "primary" or "@" in requested:
        return requested

    calendars = fetch_calendars(session)
    needle = requested.strip().lower()
    exact = [c for c in calendars if c.get("summary", "").strip().lower() == needle]
    partial = [c for c in calendars if needle in c.get("summary", "").strip().lower()]
    matches = exact or partial

    if not matches:
        names = [c.get("summary") for c in calendars]
        fail(f"לא נמצא יומן בשם '{requested}'. היומנים הקיימים: {json.dumps(names, ensure_ascii=False)}")
    if len(matches) > 1:
        names = [c.get("summary") for c in matches]
        fail(f"השם '{requested}' מתאים ליותר מיומן אחד: {json.dumps(names, ensure_ascii=False)}. ציינו שם מלא או מזהה.")
    return matches[0]["id"]


def time_field(value, timezone, all_day):
    """בונה את אובייקט start/end של האירוע לפי הפורמט שהתקבל."""
    value = value.replace(" ", "T")
    if all_day or DATE_ONLY.match(value):
        if not DATE_ONLY.match(value):
            fail(f"עבור אירוע יום-שלם נדרש תאריך בפורמט YYYY-MM-DD, התקבל: {value}")
        return {"date": value}
    if not DATE_TIME.match(value):
        fail(f"פורמט זמן לא מזוהה: {value} (צפוי YYYY-MM-DD או YYYY-MM-DDTHH:MM)")
    if len(value) == 16:
        value += ":00"
    return {"dateTime": value, "timeZone": timezone}


def derive_end(args):
    """משלים שעת סיום כשלא נמסרה - שעה אחת, או יום אחד לאירוע יום-שלם."""
    start = args.start.replace(" ", "T")
    if args.all_day or DATE_ONLY.match(start):
        # ב-Google Calendar תאריך הסיום של אירוע יום-שלם הוא בלעדי (exclusive),
        # ולכן יום בודד = למחרת. בלי זה האירוע פשוט לא ייווצר.
        day = datetime.strptime(start, "%Y-%m-%d") + timedelta(days=1)
        return day.strftime("%Y-%m-%d")
    if not DATE_TIME.match(start):
        fail(f"פורמט זמן לא מזוהה: {start} (צפוי YYYY-MM-DD או YYYY-MM-DDTHH:MM)")
    fmt = "%Y-%m-%dT%H:%M:%S" if len(start) > 16 else "%Y-%m-%dT%H:%M"
    return (datetime.strptime(start, fmt) + timedelta(minutes=args.duration)).strftime("%Y-%m-%dT%H:%M")


EVENT_FIELDS = "id,summary,description,location,start,end,status,htmlLink"


def cmd_list_calendars(args, session):
    calendars = fetch_calendars(session)
    rows = [
        {
            "id": c.get("id"),
            "name": c.get("summary"),
            "primary": bool(c.get("primary")),
            "access": c.get("accessRole"),
            "timeZone": c.get("timeZone"),
        }
        for c in calendars
    ]
    print(json.dumps({"count": len(rows), "calendars": rows}, ensure_ascii=False, indent=2))


def cmd_list_events(args, session):
    calendar_id = resolve_calendar(session, args.calendar)
    time_min = f"{args.date_from}T00:00:00" if DATE_ONLY.match(args.date_from) else args.date_from
    time_max = f"{args.date_to}T23:59:59" if DATE_ONLY.match(args.date_to) else args.date_to

    events, page_token = [], None
    while True:
        params = {
            "timeMin": time_min + _utc_offset_suffix(time_min, args.timezone),
            "timeMax": time_max + _utc_offset_suffix(time_max, args.timezone),
            "singleEvents": True,   # מפרק אירועים חוזרים למופעים בפועל, אחרת מקבלים כלל חזרה ולא תאריכים
            "orderBy": "startTime",
            "maxResults": 250,
        }
        if page_token:
            params["pageToken"] = page_token
        body = api(session, "GET", f"/calendars/{_quote(calendar_id)}/events", params=params)
        events.extend(body.get("items", []))
        page_token = body.get("nextPageToken")
        if not page_token:
            break

    rows = [
        {
            "id": e.get("id"),
            "title": e.get("summary"),
            "start": (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date"),
            "end": (e.get("end") or {}).get("dateTime") or (e.get("end") or {}).get("date"),
            "location": e.get("location"),
            "status": e.get("status"),
            "link": e.get("htmlLink"),
        }
        for e in events
    ]
    print(json.dumps({"calendar": calendar_id, "count": len(rows), "events": rows},
                     ensure_ascii=False, indent=2))


def _utc_offset_suffix(value, timezone):
    """timeMin/timeMax חייבים להיות RFC3339 עם אזור זמן; זמן נאיבי נדחה ב-400.

    ההיסט מחושב לפי התאריך עצמו ולא מקובע, כי ישראל היא +03:00 בשעון קיץ
    ו-+02:00 בחורף - קיבוע היה מזיז את גבולות הטווח בשעה בחצי מהשנה.
    """
    if re.search(r"(Z|[+\-]\d{2}:\d{2})$", value):
        return ""
    try:
        from zoneinfo import ZoneInfo
        moment = datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=ZoneInfo(timezone))
        return moment.strftime("%z")[:3] + ":" + moment.strftime("%z")[3:]
    except Exception:
        return "Z"  # נפילה לאחור ל-UTC: גבול טווח מדויק פחות, עדיף על בקשה שנדחית


def _quote(calendar_id):
    import urllib.parse
    return urllib.parse.quote(calendar_id, safe="")


def cmd_create_event(args, session):
    calendar_id = resolve_calendar(session, args.calendar)
    end = args.end or derive_end(args)

    body = {
        "summary": args.title,
        "start": time_field(args.start, args.timezone, args.all_day),
        "end": time_field(end, args.timezone, args.all_day),
    }
    if args.description:
        body["description"] = args.description
    if args.location:
        body["location"] = args.location

    created = api(session, "POST", f"/calendars/{_quote(calendar_id)}/events",
                  json=body, params={"fields": EVENT_FIELDS})
    print(json.dumps({"calendar": calendar_id, "created": created}, ensure_ascii=False, indent=2))


def cmd_update_event(args, session):
    calendar_id = resolve_calendar(session, args.calendar)

    body = {}
    if args.title:
        body["summary"] = args.title
    if args.description is not None:
        body["description"] = args.description
    if args.location is not None:
        body["location"] = args.location
    if args.start:
        body["start"] = time_field(args.start, args.timezone, args.all_day)
    if args.end:
        body["end"] = time_field(args.end, args.timezone, args.all_day)
    if args.status:
        body["status"] = args.status
    if not body:
        fail("לא נמסר שום שדה לעדכון")

    # PATCH ולא PUT: PUT מחליף את האירוע כולו, כלומר משמיט בשקט כל שדה שלא נשלח.
    updated = api(session, "PATCH", f"/calendars/{_quote(calendar_id)}/events/{_quote(args.event_id)}",
                  json=body, params={"fields": EVENT_FIELDS})
    print(json.dumps({"calendar": calendar_id, "updated": updated}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Google Calendar wrapper (OAuth, personal account)")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help=f"default {DEFAULT_TIMEZONE}")
    sub = parser.add_subparsers(dest="action", required=True)

    p_cals = sub.add_parser("list-calendars", help="list every calendar this account can see")
    p_cals.set_defaults(func=cmd_list_calendars)

    p_events = sub.add_parser("list-events", help="list events in a date range")
    p_events.add_argument("--calendar", default=None, help="calendar id, 'primary', or part of its name")
    p_events.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    p_events.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
    p_events.set_defaults(func=cmd_list_events)

    p_new = sub.add_parser("create-event", help="create a calendar event")
    p_new.add_argument("--calendar", default=None, help="calendar id, 'primary', or part of its name")
    p_new.add_argument("--title", required=True)
    p_new.add_argument("--start", required=True, help="YYYY-MM-DD (all-day) or YYYY-MM-DDTHH:MM")
    p_new.add_argument("--end", default=None, help="defaults to start + --duration (or +1 day if all-day)")
    p_new.add_argument("--duration", type=int, default=60, help="minutes, used when --end is omitted")
    p_new.add_argument("--all-day", action="store_true")
    p_new.add_argument("--description", default=None)
    p_new.add_argument("--location", default=None)
    p_new.set_defaults(func=cmd_create_event)

    p_upd = sub.add_parser("update-event", help="update fields on an existing event")
    p_upd.add_argument("--calendar", default=None, help="calendar id, 'primary', or part of its name")
    p_upd.add_argument("--event-id", required=True)
    p_upd.add_argument("--title", default=None)
    p_upd.add_argument("--start", default=None)
    p_upd.add_argument("--end", default=None)
    p_upd.add_argument("--all-day", action="store_true")
    p_upd.add_argument("--description", default=None)
    p_upd.add_argument("--location", default=None)
    p_upd.add_argument("--status", choices=["confirmed", "tentative", "cancelled"], default=None,
                       help="'cancelled' is the reversible way to call off an event - there is no delete here")
    p_upd.set_defaults(func=cmd_update_event)

    args = parser.parse_args()
    session = get_session()
    args.func(args, session)


if __name__ == "__main__":
    main()
