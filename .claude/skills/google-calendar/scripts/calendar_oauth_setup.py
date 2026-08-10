#!/usr/bin/env python3
"""
הקמה חד-פעמית (אינטראקטיבית) של הרשאת OAuth אישית ל-Google Calendar, בשביל
gcal.py. בדיוק כמו ב-drive_oauth_setup.py, זו הרשאה בשם המשתמשת עצמה ולא
service account - ליומן אישי (Gmail רגיל, לא Workspace) חשבון שירות לא יכול
לגשת ליומנים של המשתמשת בלי הרשאת domain-wide delegation, שקיימת רק ב-Workspace.

קובץ הטוקן נכתב בנפרד מזה של הדרייב (credentials/calendar-oauth-token.json)
במכוון: לטוקן של הדרייב יש scope של drive.file בלבד, והוספת scope של יומן
אליו הייתה מחייבת לדרוס אותו - כלומר לסכן זרימת עבודה שכבר עובדת. שני קבצים
נפרדים, אותו OAuth client, אפס סיכון להדדיות.

שימוש (חד-פעמי):
    python3 calendar_oauth_setup.py --client-file credentials/drive-oauth-client.json

זה יפתח דפדפן (או ידפיס קישור אם הדפדפן לא נפתח לבד), תאשרו גישה, וקובץ
טוקן ייכתב ל-credentials/calendar-oauth-token.json (ברירת מחדל).

דרישה מקדימה: Google Calendar API חייב להיות מופעל בפרויקט ה-Google Cloud
(אותו פרויקט hila-seo). קריאה מול API מושבת נכשלת ב-SERVICE_DISABLED, לא
בשגיאת הרשאה - אותה מלכודת שמתועדת אצל GA4.

דורש: pip3 install google-auth requests
"""

import argparse
import functools
import http.server
import json
import os
import sys
import threading
import urllib.parse
import webbrowser

print = functools.partial(print, flush=True)  # stdout is block-buffered when not a TTY - without this the
                                               # auth URL wouldn't appear until the process exits.

try:
    import requests
except ImportError:
    print("חסרה חבילה. הריצו: pip3 install requests", file=sys.stderr)
    sys.exit(1)

# events = יצירה/עדכון של אירועים; readonly = רשימת היומנים וקריאת אירועים.
# שניהם יחד לא מאפשרים למחוק יומן או לשנות הגדרות חשבון.
SCOPES = " ".join([
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
])
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


def load_client(client_file):
    with open(client_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    # קבצי "OAuth client ID" מסוג Desktop app מגיעים עטופים במפתח "installed";
    # מסוג Web application עטופים ב-"web". שני הפורמטים תקינים כאן.
    block = data.get("installed") or data.get("web")
    if not block:
        print("קובץ ה-client לא בפורמט צפוי (חסר מפתח installed/web)", file=sys.stderr)
        sys.exit(1)
    return block["client_id"], block["client_secret"]


class _CodeHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        self.server.auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<html><body><h2>ההרשאה התקבלה - אפשר לסגור את החלון הזה ולחזור לטרמינל.</h2></body></html>".encode("utf-8"))

    def log_message(self, format, *args):
        pass  # שקט - לא להציף את הטרמינל בלוגים של HTTP


def wait_for_code(port):
    server = http.server.HTTPServer(("127.0.0.1", port), _CodeHandler)
    server.auth_code = None
    server.timeout = 300
    server.handle_request()  # חוסם עד שמתקבלת בקשה אחת (ה-redirect עם ה-code), עד 5 דקות
    return server.auth_code


def main():
    parser = argparse.ArgumentParser(description="One-time OAuth setup for google-calendar")
    parser.add_argument("--client-file", default="credentials/drive-oauth-client.json",
                        help="path to the OAuth client JSON (the Drive one works - same Cloud project)")
    parser.add_argument("--token-file", default="credentials/calendar-oauth-token.json")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    if not os.path.isfile(args.client_file):
        print(f"קובץ ה-client לא נמצא: {args.client_file}", file=sys.stderr)
        sys.exit(1)

    client_id, client_secret = load_client(args.client_file)
    redirect_uri = f"http://127.0.0.1:{args.port}/"

    auth_url = AUTH_ENDPOINT + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    })

    print("פותח דפדפן להרשאה... אם הוא לא נפתח לבד, פתחו את הקישור הזה ידנית:")
    print(auth_url)
    threading.Timer(0.5, lambda: webbrowser.open(auth_url)).start()

    code = wait_for_code(args.port)
    if not code:
        print("לא התקבל קוד הרשאה (timeout או ביטול). נסו שוב.", file=sys.stderr)
        sys.exit(1)

    resp = requests.post(TOKEN_ENDPOINT, data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=30)

    if resp.status_code >= 400:
        print(f"חילופי הטוקן נכשלו ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)

    tokens = resp.json()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print(
            "לא התקבל refresh_token - כנראה שכבר אישרתם את ההרשאה הזו בעבר. "
            "לכו ל-https://myaccount.google.com/permissions, הסירו את הגישה של האפליקציה, ונסו שוב.",
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(os.path.dirname(args.token_file) or ".", exist_ok=True)
    with open(args.token_file, "w", encoding="utf-8") as f:
        json.dump({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "token_uri": TOKEN_ENDPOINT,
        }, f, ensure_ascii=False, indent=2)

    print(f"בוצע. קובץ הטוקן נשמר ב-{args.token_file}")
    print(f"הוסיפו ל-.env: GOOGLE_CALENDAR_OAUTH_TOKEN_FILE={args.token_file}")


if __name__ == "__main__":
    main()
