#!/usr/bin/env python3
"""crm-deals — קריאה מה-Mini CRM וכתיבה מוגבלת לטבלת עסקאות.

בייס אחד קבוע (Mini CRM), שלוש טבלאות, ורשימת שדות-כתיבה סגורה בקוד.
כל מה שמחוץ לרשימה — SUMIT, תשלומים, חומרים, פגישות — מנוהל ע"י האוטומציות
הקיימות של הילה, והסקיל הזה לא נוגע בו. אין מחיקה.
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_ID = "appcfuP4ufqhwipBm"  # Mini CRM — לא AIRTABLE_BASE_ID (שהוא בייס התוכן)

TABLES = {
    "deals": "tbl3dP8utT9rgw0AT",     # עסקאות
    "products": "tblVEXRxB0BfX1jh9",  # מוצרים
    "contacts": "tblwIo1FYWq1D8hQw",  # אנשי קשר
}

# רשימה סגורה. עדכון שדה שלא כאן ייכשל בכוונה.
DEAL_WRITABLE = {
    "מחיר העסקה",
    "תיאור",
    "מוצרים",
    "Stage",
    "סיכום לקראת שיחה",
    "סיבת הפנייה",
    "אחוז הנחה",
    "אנשי קשר",
    "שם חברה",
}

CONTACT_WRITABLE = {
    "שם פרטי",
    "שם משפחה",
    "תאריך קליטה",
    "מקור הגעה",
    "Email",
    "טלפון",
    "הצעת מחיר אחרונה",
    "הערות",
}

STAGES = [
    "ליד ⭐",
    "נוצר קשר 🤝",
    "נשלחה הצעת מחיר 📧",
    "פולואפ 📅",
    "אושרה הצעת מחיר ✅",
    "לא אושרה הצעת מחיר 👎",
    "לא רלוונטי ❌ ",  # הרווח בסוף מכוון — כך זה רשום באיירטייבל
]


def load_dotenv():
    """טוען .env מרוט הפרויקט. תת-סוכן לא יורש את סביבת המעטפת,
    ולכן הסקריפט חייב לטעון בעצמו ולא להסתמך על source ידני."""
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        env = parent / ".env"
        if not env.is_file():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
        return
    return


def api_key():
    key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        load_dotenv()
        key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        sys.exit("AIRTABLE_API_KEY חסר — לא נמצא בסביבה ולא ב-.env בשורש הפרויקט")
    return key


def request(method, path, params=None, payload=None):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(payload, ensure_ascii=False).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key()}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        sys.exit(f"Airtable {exc.code}: {body}")


def fetch_all(table, params=None):
    records, offset = [], None
    while True:
        page_params = dict(params or {})
        if offset:
            page_params["offset"] = offset
        page = request("GET", TABLES[table], params=page_params)
        records.extend(page.get("records", []))
        offset = page.get("offset")
        if not offset:
            return records


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ---------- קריאה ----------

def cmd_products(args):
    rows = []
    for rec in fetch_all("products"):
        f = rec["fields"]
        rows.append({
            "id": rec["id"],
            "מוצר": f.get("תיאור") or f.get("שם המוצר ומחיר"),
            "קטגוריה": f.get("קטגוריה"),
            "מחיר": f.get('סה"כ'),
        })
    rows.sort(key=lambda r: (r["קטגוריה"] or "zz", r["מוצר"] or ""))
    emit(rows)


def cmd_pipeline(args):
    buckets = {}
    for rec in fetch_all("deals"):
        f = rec["fields"]
        stage = f.get("Stage", "(ללא שלב)")
        buckets.setdefault(stage, []).append({
            "id": rec["id"],
            "עסקה": f.get("Opportunity Name"),
            "מחיר קטלוגי": f.get("מחיר העסקה"),
            "הנחה": f.get("אחוז הנחה"),
            "מחיר": f.get("מחיר אחרי הנחה") or f.get("מחיר העסקה"),
            "תיאור": f.get("תיאור"),
            "עודכן": (f.get("עודכן לאחרונה") or "")[:10],
        })
    if args.stage:
        buckets = {k: v for k, v in buckets.items() if args.stage in k}
    for deals in buckets.values():
        deals.sort(key=lambda d: d["עודכן"], reverse=True)
    emit({"סיכום": {k: len(v) for k, v in buckets.items()}, "עסקאות": buckets})


def cmd_find_deal(args):
    needle = args.query
    hits = []
    for rec in fetch_all("deals"):
        f = rec["fields"]
        blob = " ".join(str(v) for v in f.values())
        if needle in blob:
            hits.append({"id": rec["id"], **f})
    emit(hits)


def cmd_find_contact(args):
    hits = []
    for rec in fetch_all("contacts"):
        f = rec["fields"]
        name = f.get("Full Name") or ""
        if args.query in name or args.query in str(f.get("Email", "")):
            hits.append({
                "id": rec["id"],
                "שם": name,
                "Email": f.get("Email"),
                "טלפון": f.get("טלפון"),
                "מקור הגעה": f.get("מקור הגעה"),
                "עסקאות": f.get("עסקאות"),
            })
    emit(hits)


# ---------- כתיבה ----------

def guard(fields, allowed, label):
    blocked = set(fields) - allowed
    if blocked:
        sys.exit(
            f"שדות חסומים לכתיבה ב{label}: {', '.join(sorted(blocked))}\n"
            f"מותר רק: {', '.join(sorted(allowed))}"
        )


MAX_DISCOUNT = 0.15  # 15% — התקרה שהילה קבעה


def normalize_discount(fields):
    """מקבל 10 או 0.1 ומחזיר 0.1. חוסם מעל התקרה."""
    if "אחוז הנחה" not in fields:
        return
    v = float(fields["אחוז הנחה"])
    if v > 1:
        v /= 100
    if v > MAX_DISCOUNT:
        sys.exit(
            f"הנחה של {v:.0%} חורגת מהתקרה של {MAX_DISCOUNT:.0%}. "
            "רק הילה מאשרת חריגה, וידנית באיירטייבל."
        )
    if v < 0:
        sys.exit("אחוז הנחה שלילי")
    fields["אחוז הנחה"] = v


def check_stage(fields):
    if "Stage" in fields and fields["Stage"] not in STAGES:
        sys.exit(f"Stage לא חוקי. אפשרויות: {STAGES}")


def parse_fields(pairs):
    fields = {}
    for pair in pairs or []:
        if "=" not in pair:
            sys.exit(f"פורמט שגוי: {pair} (צריך שדה=ערך)")
        key, value = pair.split("=", 1)
        if value.startswith("[") or value.startswith("{"):
            value = json.loads(value)
        elif key in ("מחיר העסקה", "אחוז הנחה"):
            value = float(value)
        fields[key] = value
    return fields


def cmd_create_contact(args):
    fields = parse_fields(args.field)
    fields.setdefault("שם פרטי", args.first_name)
    if args.last_name:
        fields.setdefault("שם משפחה", args.last_name)
    # תאריך קליטה תמיד — בלעדיו הרשומה צוללת לתחתית התצוגה של הילה
    fields.setdefault("תאריך קליטה", datetime.datetime.now().astimezone().isoformat())
    # מקור הגעה מפורש — לשדה יש ברירת מחדל "דף נחיתה" שמתייגת שגוי בשקט
    if not fields.get("מקור הגעה"):
        sys.exit("חובה לציין מקור הגעה מפורש (--field 'מקור הגעה=המלצה')")
    guard(fields, CONTACT_WRITABLE, "אנשי קשר")
    res = request("POST", TABLES["contacts"], payload={"fields": fields})
    emit({"נוצר": res["id"], "שדות": res["fields"]})


def cmd_create_deal(args):
    fields = parse_fields(args.field)
    fields.setdefault("Stage", "נוצר קשר 🤝")
    if args.contact:
        fields["אנשי קשר"] = [args.contact]
    guard(fields, DEAL_WRITABLE, "עסקאות")
    check_stage(fields)
    normalize_discount(fields)
    res = request("POST", TABLES["deals"], payload={"fields": fields})
    emit({"נוצר": res["id"], "שדות": res["fields"]})


def cmd_update_deal(args):
    fields = parse_fields(args.field)
    if not fields:
        sys.exit("לא ניתן שום שדה לעדכון")
    guard(fields, DEAL_WRITABLE, "עסקאות")
    check_stage(fields)
    normalize_discount(fields)
    res = request(
        "PATCH",
        f"{TABLES['deals']}/{args.record}",
        payload={"fields": fields},
    )
    emit({"עודכן": res["id"], "שדות": res["fields"]})


def main():
    parser = argparse.ArgumentParser(description="Mini CRM — קריאה וכתיבה מוגבלת")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-products").set_defaults(func=cmd_products)

    p = sub.add_parser("pipeline")
    p.add_argument("--stage", help="סינון לשלב מסוים")
    p.set_defaults(func=cmd_pipeline)

    p = sub.add_parser("find-deal")
    p.add_argument("query")
    p.set_defaults(func=cmd_find_deal)

    p = sub.add_parser("find-contact")
    p.add_argument("query")
    p.set_defaults(func=cmd_find_contact)

    p = sub.add_parser("create-contact")
    p.add_argument("first_name")
    p.add_argument("--last-name")
    p.add_argument("--field", action="append")
    p.set_defaults(func=cmd_create_contact)

    p = sub.add_parser("create-deal")
    p.add_argument("--contact", help="record id של איש הקשר")
    p.add_argument("--field", action="append")
    p.set_defaults(func=cmd_create_deal)

    p = sub.add_parser("update-deal")
    p.add_argument("record")
    p.add_argument("--field", action="append")
    p.set_defaults(func=cmd_update_deal)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
