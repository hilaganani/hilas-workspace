#!/usr/bin/env python3
"""
יוצר טיוטת קמפיין (Campaign) חדשה בסמוב מתוך HTML מוכן. אינו שולח -
זו פעולה מכוונת: השליחה בפועל נשארת פעולה ידנית של המשתמשת בממשק סמוב.

שימוש:
    python3 create_draft.py --subject "כותרת הניוזלטר" --html-file path/to/newsletter.html

דורש ב-.env:
    SMOOVE_API_KEY  - מפתח API מסמוב (Account name > API Keys & pixels > Add API Key)
    SMOOVE_LIST_ID  - מזהה הרשימה המספרי לשליחה (ראו --list-lists לאיתור)

דורש: pip3 install requests
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print(
        json.dumps({"error": "חסרה חבילת requests. הריצו: pip3 install requests"}, ensure_ascii=False)
    )
    sys.exit(1)

API_BASE = "https://rest.smoove.io/v1"


def get_headers():
    api_key = os.environ.get("SMOOVE_API_KEY")
    if not api_key:
        print(json.dumps({"error": "SMOOVE_API_KEY לא מוגדר ב-.env"}, ensure_ascii=False))
        sys.exit(1)
    # מאומת מול קריאה אמיתית (2026-07-14): Authorization עם המפתח הגולמי, בלי "Bearer".
    return {"Authorization": api_key, "Content-Type": "application/json"}


def cmd_list_lists(args):
    resp = requests.get(f"{API_BASE}/Lists", headers=get_headers(), timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def cmd_list_templates(args):
    resp = requests.get(f"{API_BASE}/Campaigns_Templates", headers=get_headers(), timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def cmd_create_draft(args):
    list_id = os.environ.get("SMOOVE_LIST_ID")
    if not list_id:
        print(json.dumps({"error": "SMOOVE_LIST_ID לא מוגדר ב-.env - הריצו list-lists כדי לאתר אותו"}, ensure_ascii=False))
        sys.exit(1)

    with open(args.html_file, encoding="utf-8") as f:
        html_body = f.read()

    payload = {
        "subject": args.subject,
        "body": html_body,
        "toListsById": [int(list_id)],
        "trackLinks": True,
    }
    # אזהרה: לעולם אל תוסיפו כאן sendnow=true או scheduleto - אלה גורמים לסמוב לשלוח/לתזמן
    # בפועל, וזה מפר את העיקרון המרכזי של הסקיל הזה (טיוטה בלבד, שליחה תמיד ידנית).
    params = {}
    template_id = args.template_name or os.environ.get("SMOOVE_TEMPLATE_ID")
    if template_id:
        params["templateId"] = template_id
    resp = requests.post(f"{API_BASE}/Campaigns", headers=get_headers(), json=payload, params=params, timeout=30)

    if resp.status_code >= 400:
        print(json.dumps({"error": "יצירת הטיוטה נכשלה", "status": resp.status_code, "body": resp.text}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    print(
        "\nהטיוטה נוצרה בסמוב. היא לא נשלחה - יש לפתוח את הקמפיין בממשק סמוב (Campaigns) ולשלוח אותו ידנית.",
        file=sys.stderr,
    )


def main():
    parser = argparse.ArgumentParser(description="Smoove campaign draft creator (never sends)")
    sub = parser.add_subparsers(dest="action", required=True)

    p_create = sub.add_parser("create-draft", help="create a draft campaign from an HTML file")
    p_create.add_argument("--subject", required=True)
    p_create.add_argument("--html-file", required=True)
    p_create.add_argument("--template-name", default=None, help="template id from list-templates; falls back to SMOOVE_TEMPLATE_ID env var")
    p_create.set_defaults(func=cmd_create_draft)

    p_lists = sub.add_parser("list-lists", help="list available contact lists and their IDs")
    p_lists.set_defaults(func=cmd_list_lists)

    p_templates = sub.add_parser("list-templates", help="list available design templates and their IDs")
    p_templates.set_defaults(func=cmd_list_templates)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
