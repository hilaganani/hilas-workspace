#!/usr/bin/env python3
"""
יוצר ומעדכן רשומות בטבלת "תכנון תוכן חודשי" ב-Airtable (tbl6S09qb9wK2ARW6) -
מקור האמת ליומן תכנון-מול-ביצוע (ראו CLAUDE.md, סעיף "Feedback loop: plan vs. actual").

שתי פעולות בלבד, לפי עקרון הרשאות מינימליות:
    create-items  - יצירת שורות חדשות (סטטוס תמיד "מתוכנן")
    update-items  - עדכון סטטוס/הערה/קישור-גרסה-סופית בלבד, לפי "מספר סידורי"
                    (לעולם לא שדות אסטרטגיה: שבוע/ערוץ/נושא, לעולם לא מחיקה,
                    לעולם לא טבלה אחרת)

שימוש:
    python3 content_calendar.py create-items --items-json items.json
    python3 content_calendar.py update-items --updates-json updates.json

דורש ב-.env:
    AIRTABLE_API_KEY, AIRTABLE_BASE_ID (אותם משתנים כמו airtable-read/airtable-write)

דורש: pip3 install requests
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print(json.dumps({"error": "חסרה חבילת requests. הריצו: pip3 install requests"}, ensure_ascii=False))
    sys.exit(1)

TABLE_ID = "tbl6S09qb9wK2ARW6"  # תכנון תוכן חודשי
API_BASE = "https://api.airtable.com/v0"

ALLOWED_CHANNELS = {"בלוג", "ניוזלטר", "לינקדאין", "פייסבוק/אינסטגרם", "טיקטוק"}
ALLOWED_STATUSES = {"פורסם", "שונה", "לא עלה"}
DEFAULT_STATUS = "מתוכנן"
BATCH_SIZE = 10  # מגבלת Airtable ליצירה/עדכון מרובה-רשומות בקריאה אחת


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def build_create_fields(item):
    channel = item["channel"]
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"ערוץ לא מוכר: {channel!r} (מותר: {sorted(ALLOWED_CHANNELS)})")
    return {
        "שבוע / תאריך יעד": item["week_or_date"],
        "ערוץ": channel,
        "נושא": item["topic"],
        "סטטוס": DEFAULT_STATUS,
    }


def build_update_fields(update):
    status = update["status"]
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"סטטוס לא מוכר: {status!r} (מותר: {sorted(ALLOWED_STATUSES)})")
    fields = {"סטטוס": status}
    if update.get("note"):
        fields["הערה"] = update["note"]
    if update.get("final_link"):
        fields["קישור/גרסה סופית"] = update["final_link"]
    return fields


if __name__ == "__main__":
    print(json.dumps({"error": "CLI not implemented yet — see Task 2/3"}, ensure_ascii=False))
    sys.exit(1)
