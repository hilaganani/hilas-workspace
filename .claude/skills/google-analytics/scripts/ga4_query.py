#!/usr/bin/env python3
"""
קורא ל-Google Analytics 4 Data API עם service account, בלי לחשוף את ה-access
token בפלט בשום שלב (האסימון נשאר פנימי לתהליך; רק תוצאת הנתונים מודפסת).

שימוש:
    python3 ga4_query.py list-properties
    python3 ga4_query.py report --start-date 2026-08-20 --end-date 2026-08-31 \
        --dimensions sessionSource,sessionCampaignName --metrics sessions,activeUsers
    python3 ga4_query.py realtime

דורש ב-.env:
    GA4_PROPERTY_ID              - מזהה מספרי של הנכס (לא G-XXXX). למצוא: list-properties
    GOOGLE_ANALYTICS_KEY_FILE    - נתיב לקובץ מפתח JSON של service account.
                                   אם לא מוגדר, נופל חזרה ל-GOOGLE_SEARCH_CONSOLE_KEY_FILE
                                   (אותו חשבון שירות משמש את שני הסקילים).

דורש: pip3 install google-auth requests
"""

import argparse
import json
import os
import sys

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
except ImportError:
    print(
        "חסרות חבילות. הריצו: pip3 install google-auth requests",
        file=sys.stderr,
    )
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
DATA_API_BASE = "https://analyticsdata.googleapis.com/v1beta"
ADMIN_API_BASE = "https://analyticsadmin.googleapis.com/v1beta"


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False))
    sys.exit(1)


def get_session():
    key_file = os.environ.get("GOOGLE_ANALYTICS_KEY_FILE") or os.environ.get(
        "GOOGLE_SEARCH_CONSOLE_KEY_FILE"
    )
    if not key_file or not os.path.isfile(key_file):
        fail(
            "לא נמצא קובץ מפתח: הגדירו GOOGLE_ANALYTICS_KEY_FILE (או "
            "GOOGLE_SEARCH_CONSOLE_KEY_FILE) ב-.env, ובדקו שהקובץ קיים"
        )
    credentials = service_account.Credentials.from_service_account_file(
        key_file, scopes=SCOPES
    )
    # AuthorizedSession מטפל ברענון האסימון פנימית - הוא לעולם לא נחשף החוצה.
    return AuthorizedSession(credentials)


def property_id():
    prop = os.environ.get("GA4_PROPERTY_ID")
    if not prop:
        fail("GA4_PROPERTY_ID לא מוגדר ב-.env. הריצו list-properties כדי למצוא אותו")
    return prop.strip().replace("properties/", "")


def emit(resp):
    """מדפיס תשובת API. שגיאת HTTP מודפסת כמו שהיא - היא מכילה את הסיבה
    (API לא מופעל, אין הרשאה, נכס לא קיים) ואת הקישור לתיקון."""
    try:
        body = resp.json()
    except ValueError:
        fail(f"תשובה לא צפויה מה-API (HTTP {resp.status_code}): {resp.text[:500]}")
    print(json.dumps(body, ensure_ascii=False, indent=2))
    if not resp.ok:
        sys.exit(1)


def cmd_list_properties(args, session):
    """מחזיר את כל הנכסים שחשבון השירות מורשה לקרוא - כך מוצאים את
    GA4_PROPERTY_ID המספרי, שאינו זהה למזהה המדידה G-XXXXXXXXXX."""
    resp = session.get(f"{ADMIN_API_BASE}/accountSummaries", timeout=30)
    emit(resp)


def cmd_report(args, session):
    body = {
        "dateRanges": [{"startDate": args.start_date, "endDate": args.end_date}],
        "dimensions": [{"name": d} for d in args.dimensions.split(",") if d],
        "metrics": [{"name": m} for m in args.metrics.split(",") if m],
        "limit": args.limit,
    }
    if args.order_by:
        body["orderBys"] = [
            {"metric": {"metricName": args.order_by}, "desc": not args.ascending}
        ]
    if args.filter:
        if "=" not in args.filter:
            fail("--filter חייב להיות בפורמט dimensionName=value, למשל hostname=courses.ganani.co.il")
        name, value = args.filter.split("=", 1)
        body["dimensionFilter"] = {
            "filter": {
                "fieldName": name,
                "stringFilter": {"matchType": "EXACT", "value": value},
            }
        }
    resp = session.post(
        f"{DATA_API_BASE}/properties/{property_id()}:runReport", json=body, timeout=60
    )
    emit(resp)


def cmd_realtime(args, session):
    """נתוני 30 הדקות האחרונות - הדרך לוודא שהתג באמת יורה אחרי התקנה,
    בלי להמתין 24-48 שעות לדוחות הרגילים."""
    body = {
        "dimensions": [{"name": d} for d in args.dimensions.split(",") if d],
        "metrics": [{"name": "activeUsers"}],
        "limit": args.limit,
    }
    resp = session.post(
        f"{DATA_API_BASE}/properties/{property_id()}:runRealtimeReport",
        json=body,
        timeout=30,
    )
    emit(resp)


def main():
    parser = argparse.ArgumentParser(description="Google Analytics 4 Data API wrapper")
    sub = parser.add_subparsers(dest="action", required=True)

    p_list = sub.add_parser(
        "list-properties", help="כל הנכסים שחשבון השירות מורשה לקרוא (למציאת GA4_PROPERTY_ID)"
    )
    p_list.set_defaults(func=cmd_list_properties)

    p_report = sub.add_parser("report", help="דוח סטנדרטי לפי מימדים ומדדים")
    p_report.add_argument("--start-date", required=True, help="YYYY-MM-DD או NdaysAgo")
    p_report.add_argument("--end-date", required=True, help="YYYY-MM-DD או today")
    p_report.add_argument(
        "--dimensions",
        default="sessionSource",
        help="מופרד בפסיקים, למשל sessionSource,sessionCampaignName,hostname,pagePath",
    )
    p_report.add_argument(
        "--metrics",
        default="sessions",
        help="מופרד בפסיקים, למשל sessions,activeUsers,screenPageViews",
    )
    p_report.add_argument("--limit", type=int, default=50)
    p_report.add_argument("--order-by", default=None, help="שם מדד למיון, למשל sessions")
    p_report.add_argument("--ascending", action="store_true", help="מיון עולה במקום יורד")
    p_report.add_argument(
        "--filter", default=None, help="סינון מדויק בפורמט dimensionName=value"
    )
    p_report.set_defaults(func=cmd_report)

    p_realtime = sub.add_parser("realtime", help="משתמשים פעילים ב-30 הדקות האחרונות")
    p_realtime.add_argument("--dimensions", default="unifiedScreenName")
    p_realtime.add_argument("--limit", type=int, default=20)
    p_realtime.set_defaults(func=cmd_realtime)

    args = parser.parse_args()
    session = get_session()
    args.func(args, session)


if __name__ == "__main__":
    main()
