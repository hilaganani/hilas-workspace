#!/usr/bin/env python3
"""
יוצר ומעדכן רשומות בטבלת "תכנון תוכן חודשי" ב-Airtable (tbl86pJ76WWc3moL2) -
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

TABLE_ID = "tbl86pJ76WWc3moL2"  # תכנון תוכן חודשי (נוצרה מחדש 2026-07-16, מזהה חדש)
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


def get_env():
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = os.environ.get("AIRTABLE_BASE_ID")
    if not api_key or not base_id:
        print(json.dumps({"error": "AIRTABLE_API_KEY ו/או AIRTABLE_BASE_ID לא מוגדרים ב-.env"}, ensure_ascii=False))
        sys.exit(1)
    return api_key, base_id


def get_headers(api_key):
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def cmd_create_items(args):
    api_key, base_id = get_env()
    with open(args.items_json, encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print(json.dumps({"error": "רשימת הפריטים ריקה"}, ensure_ascii=False))
        sys.exit(1)

    try:
        records = [{"fields": build_create_fields(item)} for item in items]
    except (KeyError, ValueError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

    created = []
    for batch in chunked(records, BATCH_SIZE):
        resp = requests.post(
            f"{API_BASE}/{base_id}/{TABLE_ID}",
            headers=get_headers(api_key),
            json={"records": batch},
            timeout=30,
        )
        if resp.status_code >= 400:
            print(json.dumps(
                {"error": "יצירת פריטים נכשלה", "status": resp.status_code, "body": resp.text, "created_so_far": len(created)},
                ensure_ascii=False, indent=2,
            ))
            sys.exit(1)
        created.extend(resp.json().get("records", []))

    print(json.dumps({"created": len(created), "records": created}, ensure_ascii=False, indent=2))


def find_record_by_serial(api_key, base_id, serial):
    formula = f"{{מספר סידורי}} = {int(serial)}"
    resp = requests.get(
        f"{API_BASE}/{base_id}/{TABLE_ID}",
        headers=get_headers(api_key),
        params={"filterByFormula": formula, "maxRecords": 1},
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"חיפוש רשומה #{serial} נכשל: {resp.status_code} {resp.text}")
    records = resp.json().get("records", [])
    return records[0]["id"] if records else None


def cmd_update_items(args):
    api_key, base_id = get_env()
    with open(args.updates_json, encoding="utf-8") as f:
        updates = json.load(f)

    if not updates:
        print(json.dumps({"error": "רשימת העדכונים ריקה"}, ensure_ascii=False))
        sys.exit(1)

    results = []
    for update in updates:
        serial = update["serial"]
        try:
            fields = build_update_fields(update)
            record_id = find_record_by_serial(api_key, base_id, serial)
        except (KeyError, ValueError, RuntimeError) as e:
            results.append({"serial": serial, "error": str(e)})
            continue

        if record_id is None:
            results.append({"serial": serial, "error": f"לא נמצאה רשומה עם מספר סידורי {serial}"})
            continue

        resp = requests.patch(
            f"{API_BASE}/{base_id}/{TABLE_ID}/{record_id}",
            headers=get_headers(api_key),
            json={"fields": fields},
            timeout=30,
        )
        if resp.status_code >= 400:
            results.append({"serial": serial, "error": f"עדכון נכשל: {resp.status_code} {resp.text}"})
            continue

        results.append({"serial": serial, "updated": True, "record_id": record_id, "fields": fields})

    failed = [r for r in results if "error" in r]
    print(json.dumps(
        {"results": results, "succeeded": len(results) - len(failed), "failed": len(failed)},
        ensure_ascii=False, indent=2,
    ))
    if failed:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Airtable content-calendar create+restricted-update (תכנון תוכן חודשי)")
    sub = parser.add_subparsers(dest="action", required=True)

    p_create = sub.add_parser("create-items", help="create new planned rows (status always מתוכנן)")
    p_create.add_argument("--items-json", required=True, help="JSON file: array of {week_or_date, channel, topic}")
    p_create.set_defaults(func=cmd_create_items)

    p_update = sub.add_parser("update-items", help="update status/note/final_link only, by מספר סידורי")
    p_update.add_argument("--updates-json", required=True, help="JSON file: array of {serial, status, note?, final_link?}")
    p_update.set_defaults(func=cmd_update_items)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
