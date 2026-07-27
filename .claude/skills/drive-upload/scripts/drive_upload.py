#!/usr/bin/env python3
"""
מעלה קבצים מקומיים (כל סוג - טקסט או בינארי, כולל תמונות) ל-Google Drive
דרך הרשאת OAuth אישית, בלי להעביר את תוכן הקובץ דרך שום LLM context - הסקריפט
קורא את הקובץ מהדיסק וזורם אותו ישירות ל-API.

הערה: לא נעשה שימוש ב-service account כאן, כי לחשבונות שירות אין מכסת אחסון
בדרייב אישי (Gmail רגיל, לא Google Workspace) - כל ניסיון העלאה נכשל ב-403
"Service Accounts do not have storage quota", גם כשהתיקייה משותפת עם ה-service
account. OAuth בשם המשתמשת עצמה הוא הדרך הנכונה היחידה עבור Gmail אישי.

הקמה חד-פעמית: ראו scripts/drive_oauth_setup.py.

שימוש:
    python3 drive_upload.py whoami
    python3 drive_upload.py create-folder --name "שם התיקייה" --parent <folder_id>
    python3 drive_upload.py upload --file /path/to/file.png --parent <folder_id> [--name "שם.png"]

דורש ב-.env:
    GOOGLE_DRIVE_OAUTH_TOKEN_FILE - נתיב לקובץ הטוקן שנוצר ע"י drive_oauth_setup.py

דורש: pip3 install google-auth requests
"""

import argparse
import json
import mimetypes
import os
import sys

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import AuthorizedSession
except ImportError:
    print(
        "חסרות חבילות. הריצו: pip3 install google-auth requests",
        file=sys.stderr,
    )
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FILES_URL = "https://www.googleapis.com/drive/v3/files"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
ABOUT_URL = "https://www.googleapis.com/drive/v3/about"


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False))
    sys.exit(1)


def token_file_path():
    token_file = os.environ.get("GOOGLE_DRIVE_OAUTH_TOKEN_FILE")
    if not token_file or not os.path.isfile(token_file):
        fail(
            "GOOGLE_DRIVE_OAUTH_TOKEN_FILE לא מוגדר או שהקובץ לא נמצא - "
            "הריצו קודם python3 drive_oauth_setup.py --client-file <path>"
        )
    return token_file


def get_session():
    with open(token_file_path(), "r", encoding="utf-8") as f:
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


def cmd_whoami(args):
    session = get_session()
    resp = session.get(ABOUT_URL, params={"fields": "user"}, timeout=30)
    if resp.status_code >= 400:
        fail(f"בדיקת זהות נכשלה ({resp.status_code}): {resp.text}")
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def cmd_trash(args, session):
    resp = session.patch(
        f"{FILES_URL}/{args.file_id}",
        json={"trashed": True},
        params={"fields": "id,name,trashed"},
        timeout=30,
    )
    if resp.status_code >= 400:
        fail(f"העברה לאשפה נכשלה ({resp.status_code}): {resp.text}")
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def cmd_create_folder(args, session):
    body = {
        "name": args.name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if args.parent:
        body["parents"] = [args.parent]
    resp = session.post(FILES_URL, json=body, params={"fields": "id,name,webViewLink,parents"}, timeout=30)
    if resp.status_code >= 400:
        fail(f"יצירת תיקייה נכשלה ({resp.status_code}): {resp.text}")
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def cmd_upload(args, session):
    if not os.path.isfile(args.file):
        fail(f"הקובץ לא נמצא: {args.file}")

    name = args.name or os.path.basename(args.file)
    mime_type = args.mime_type or mimetypes.guess_type(name)[0] or "application/octet-stream"

    metadata = {"name": name}
    if args.parent:
        metadata["parents"] = [args.parent]

    with open(args.file, "rb") as fh:
        file_bytes = fh.read()

    files = {
        "metadata": (None, json.dumps(metadata), "application/json; charset=UTF-8"),
        "file": (name, file_bytes, mime_type),
    }
    resp = session.post(
        UPLOAD_URL,
        params={"uploadType": "multipart", "fields": "id,name,webViewLink,parents,size"},
        files=files,
        timeout=120,
    )
    if resp.status_code >= 400:
        fail(f"העלאה נכשלה ({resp.status_code}): {resp.text}")
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Google Drive upload wrapper (OAuth, personal account)")
    sub = parser.add_subparsers(dest="action", required=True)

    p_whoami = sub.add_parser("whoami", help="show which Google account this is authorized as")
    p_whoami.set_defaults(func=cmd_whoami)

    p_folder = sub.add_parser("create-folder", help="create a Drive folder")
    p_folder.add_argument("--name", required=True)
    p_folder.add_argument("--parent", default=None, help="parent folder id")
    p_folder.set_defaults(func=cmd_create_folder)

    p_upload = sub.add_parser("upload", help="upload a local file to a Drive folder")
    p_upload.add_argument("--file", required=True, help="local path to the file to upload")
    p_upload.add_argument("--parent", required=True, help="target folder id")
    p_upload.add_argument("--name", default=None, help="override the uploaded file's name (defaults to local filename)")
    p_upload.add_argument("--mime-type", default=None, help="override the content mime type (auto-detected by default)")
    p_upload.set_defaults(func=cmd_upload)

    p_trash = sub.add_parser("trash", help="move a Drive file to trash (reversible, not permanent delete)")
    p_trash.add_argument("--file-id", required=True, help="Drive file id to trash")
    p_trash.set_defaults(func=cmd_trash)

    args = parser.parse_args()

    if args.action == "whoami":
        args.func(args)
        return

    session = get_session()
    args.func(args, session)


if __name__ == "__main__":
    main()
