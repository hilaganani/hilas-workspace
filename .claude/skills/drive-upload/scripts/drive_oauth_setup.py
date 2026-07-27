#!/usr/bin/env python3
"""
הקמה חד-פעמית (אינטראקטיבית) של הרשאת OAuth אישית ל-Google Drive, בשביל
drive_upload.py. בניגוד ל-service account (שאין לו מכסת אחסון בדרייב אישי -
ראו את הודעת השגיאה "Service Accounts do not have storage quota"), זרימת
OAuth הזו מאשרת גישה בשם המשתמשת עצמה, ולכן ההעלאות נכנסות למכסה שלה.

שימוש (חד-פעמי):
    python3 drive_oauth_setup.py --client-file /path/to/oauth-client.json

זה יפתח דפדפן (או ידפיס קישור אם הדפדפן לא נפתח לבד), תאשרו גישה, וקובץ
טוקן ייכתב ל-credentials/drive-oauth-token.json (ברירת מחדל) - הקובץ הזה
הוא כל מה שדרוש לריצות הבאות של drive_upload.py.

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

print = functools.partial(print, flush=True)  # stdout is block-buffered when not a TTY (e.g. backgrounded) -
                                               # without this the auth URL below wouldn't appear until the
                                               # process exits, defeating the point of printing it early.

try:
    import requests
except ImportError:
    print("חסרה חבילה. הריצו: pip3 install requests", file=sys.stderr)
    sys.exit(1)

SCOPES = "https://www.googleapis.com/auth/drive.file"
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
    parser = argparse.ArgumentParser(description="One-time OAuth setup for drive-upload")
    parser.add_argument("--client-file", required=True, help="path to the downloaded OAuth client JSON")
    parser.add_argument("--token-file", default="credentials/drive-oauth-token.json")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

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
            "לא התקבל refresh_token - כנראה שכבר אישרתם את האפליקציה הזו בעבר. "
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
    print(f"הוסיפו ל-.env: GOOGLE_DRIVE_OAUTH_TOKEN_FILE={args.token_file}")


if __name__ == "__main__":
    main()
