#!/usr/bin/env python3
"""
קורא ל-Google Search Console API עם service account, בלי לחשוף את ה-access
token בפלט בשום שלב (האסימון נשאר פנימי לתהליך; רק תוצאת הנתונים מודפסת).

שימוש:
    python3 gsc_query.py search-analytics --start-date 2026-06-01 --end-date 2026-06-30 --dimensions query,page
    python3 gsc_query.py inspect --url https://example.com/some-page
    python3 gsc_query.py sitemaps

דורש ב-.env:
    GOOGLE_SEARCH_CONSOLE_KEY_FILE - נתיב לקובץ מפתח JSON של service account
    GOOGLE_SEARCH_CONSOLE_SITE_URL - כתובת ה-property, למשל sc-domain:example.com
                                      או https://example.com/

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

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
SEARCH_ANALYTICS_BASE = "https://www.googleapis.com/webmasters/v3/sites"
URL_INSPECTION_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SITEMAPS_BASE = "https://www.googleapis.com/webmasters/v3/sites"


def get_session():
    key_file = os.environ.get("GOOGLE_SEARCH_CONSOLE_KEY_FILE")
    if not key_file or not os.path.isfile(key_file):
        print(
            json.dumps(
                {"error": "GOOGLE_SEARCH_CONSOLE_KEY_FILE לא מוגדר או שהקובץ לא נמצא"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)
    credentials = service_account.Credentials.from_service_account_file(
        key_file, scopes=SCOPES
    )
    # AuthorizedSession מטפל ברענון האסימון פנימית - הוא לעולם לא נחשף החוצה.
    return AuthorizedSession(credentials)


def site_url():
    site = os.environ.get("GOOGLE_SEARCH_CONSOLE_SITE_URL")
    if not site:
        print(
            json.dumps(
                {"error": "GOOGLE_SEARCH_CONSOLE_SITE_URL לא מוגדר ב-.env"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)
    return site


def cmd_search_analytics(args, session):
    from urllib.parse import quote

    url = f"{SEARCH_ANALYTICS_BASE}/{quote(site_url(), safe='')}/searchAnalytics/query"
    body = {
        "startDate": args.start_date,
        "endDate": args.end_date,
        "dimensions": args.dimensions.split(",") if args.dimensions else ["query"],
        "rowLimit": args.row_limit,
    }
    filters = []
    if args.url_filter:
        filters.append({"dimension": "page", "operator": "equals", "expression": args.url_filter})
    if args.country:
        filters.append({"dimension": "country", "operator": "equals", "expression": args.country})
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    resp = session.post(url, json=body, timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def cmd_inspect(args, session):
    body = {"inspectionUrl": args.url, "siteUrl": site_url()}
    resp = session.post(URL_INSPECTION_URL, json=body, timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def cmd_sitemaps(args, session):
    from urllib.parse import quote

    url = f"{SITEMAPS_BASE}/{quote(site_url(), safe='')}/sitemaps"
    resp = session.get(url, timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Google Search Console API wrapper")
    sub = parser.add_subparsers(dest="action", required=True)

    p_search = sub.add_parser("search-analytics", help="clicks/impressions/position by query/page/date")
    p_search.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    p_search.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    p_search.add_argument("--dimensions", default="query", help="comma-separated: query,page,date,country,device")
    p_search.add_argument("--row-limit", type=int, default=100)
    p_search.add_argument("--url-filter", default=None, help="limit to one specific page URL")
    p_search.add_argument("--country", default=None, help="limit to one country, ISO 3166-1 alpha-3 lowercase, e.g. isr")
    p_search.set_defaults(func=cmd_search_analytics)

    p_inspect = sub.add_parser("inspect", help="real indexability status for one URL")
    p_inspect.add_argument("--url", required=True)
    p_inspect.set_defaults(func=cmd_inspect)

    p_sitemaps = sub.add_parser("sitemaps", help="list submitted sitemaps and their status")
    p_sitemaps.set_defaults(func=cmd_sitemaps)

    args = parser.parse_args()
    session = get_session()
    args.func(args, session)


if __name__ == "__main__":
    main()
