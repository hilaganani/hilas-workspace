---
name: drive-upload
description: מעטפת (wrapper) להעלאת קבצים מקומיים ל-Google Drive דרך הרשאת OAuth אישית - כולל קבצים בינאריים (תמונות PNG/JPEG), לא רק טקסט. הסקריפט קורא את הקובץ ישירות מהדיסק וזורם אותו ל-API - תוכן הקובץ לעולם לא עובר דרך שיחת ה-LLM, ולכן זה הדרך הנכונה להעלות תמונות (בניגוד לחיבור ה-MCP הישיר לדרייב, שבו העלאת תמונה דורשת קידוד base64 בתוך פרמטר טקסטואלי - יקר מאוד ב"טוקנים" ולא מעשי מעבר לתמונה בודדת קטנה). משמש כל סוכן עם גישת Bash (מירב, נגה, יעל, רועי) להעלות תוצרים גרפיים/טקסטואליים בעצמם. חשוב: משתמש ב-OAuth בשם המשתמשת עצמה, לא ב-service account - חשבונות שירות אין להם מכסת אחסון בדרייב אישי (Gmail רגיל) ולכן לא יכולים להעלות קבצים אליו בשום אופן, גם אם התיקייה משותפת איתם. דורש GOOGLE_DRIVE_OAUTH_TOKEN_FILE מוגדר ב-.env (נוצר ע"י scripts/drive_oauth_setup.py בהקמה חד-פעמית), ואת חבילות הפייתון google-auth ו-requests.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/drive_upload.py *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/drive_oauth_setup.py *)
---

# drive-upload — העלאת קבצים ל-Google Drive בלי לעבור דרך ה-LLM context

## מטרה והיקף

מעלה קבצים מקומיים (כל סוג - `.html`/`.md` טקסטואליים, וגם `.png`/`.jpg` בינאריים) ל-Google Drive, בהרשאת OAuth בשם המשתמשת. ההבדל הקריטי מול חיבור ה-Drive MCP הקיים בשיחה הראשית: הסקריפט הזה **קורא את הקובץ ישירות מהדיסק ומעביר אותו ב-HTTP request** - תוכן הקובץ לא עובר בשום שלב דרך ההקשר (context) של ה-LLM.

**למה זה חשוב**: העלאת קובץ בינארי (תמונה) דרך כלי MCP רגיל דורשת לקודד אותה כ-base64 ולהעביר אותה כפרמטר טקסטואלי בתוך קריאת הכלי - כלומר, ה-LLM "קורא" וגם "כותב" את כל התוכן המקודד. עבור טקסט זה זול, אבל עבור תמונות בינאריות ה-tokenizer מתייחס ל-base64 ביעילות גרועה מאוד (בערך 1-2 טוקנים לכל תו) - אפילו תמונה מכווצת בגודל 30-40KB יכולה לעלות עשרות אלפי טוקנים, וכמה תמונות יכולות לצרוך מאות אלפי טוקנים. הסקריפט הזה עוקף את הבעיה כליל, כי ה-LLM רק מפעיל פקודת שורת-פקודה עם נתיב לקובץ - לא "רואה" את הבייטים בעצמו.

## למה OAuth ולא service account

הניסיון הראשון בפרויקט הזה היה עם service account (בדומה ל-`google-search-console`) - זה **נכשל בעקביות** עם `403: Service Accounts do not have storage quota`, גם אחרי ששיתפו את תיקיית היעד עם כתובת המייל של חשבון השירות. זו מגבלה עקרונית של גוגל: חשבונות שירות פשוט אין להם מכסת אחסון משלהם בדרייב אישי (Gmail רגיל, לא Google Workspace) - הפתרון היחיד ל-Workspace הוא Shared Drives, שלא קיים בחשבון אישי. לכן הסקיל הזה משתמש ב-OAuth "authorization code" (עם `access_type=offline` כדי לקבל `refresh_token` שמאפשר גישה מתמשכת בלי אישור חוזר) - הקבצים מועלים ממש בשם המשתמשת, לתוך המכסה שלה.

## הקדמה חשובה: זה דורש הקמה חד-פעמית

1. ב-[console.cloud.google.com](https://console.cloud.google.com): באותו פרויקט שכבר מפעיל את `google-search-console` (או פרויקט חדש) - ודאו ש-**"Google Drive API"** מופעל (Enable).
2. אם עדיין אין מסך הסכמת OAuth (OAuth consent screen) מוגדר בפרויקט: **APIs & Services → OAuth consent screen** → סוג External → מלאו שם אפליקציה + מייל תמיכה → בשלב Test users הוסיפו את כתובת ה-Gmail שלכם עצמכם (מספיק, אין צורך לפרסם את האפליקציה).
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → סוג אפליקציה: **Desktop app** → תנו שם כלשהו → Create. הורידו את קובץ ה-JSON שנוצר (הכפתור "Download JSON").
4. שמרו את הקובץ **מחוץ לגיט**, למשל `credentials/drive-oauth-client.json`.
5. **חשוב, זו הסיבה הכי שכיחה לכישלון**: ב-**Audience** (בתפריט הצד של ה-Google Auth Platform), תחת "Test users", לחצו **+ Add users** והוסיפו את כתובת ה-Gmail שלכם עצמכם. בלי זה, כל ניסיון הרשאה נחסם לגמרי עם השגיאה "Access blocked - Google's verification process has not completed", גם אם ה-scope הנכון כבר מוצהר.
6. עדיין ב-Google Auth Platform, תחת **Data Access**, לחצו **Add or remove scopes** והוסיפו את `https://www.googleapis.com/auth/drive.file` (הוספת ה-scope כאן חובה - אם ה-scope לא מוצהר במסך הזה, בקשת הרשאה בזמן ריצה עם אותו scope תיחסם, גם אם הוא לא scope "מוגבל").
7. הריצו את ההרשאה החד-פעמית (זה יפתח דפדפן, תתבקשו להתחבר ולאשר גישה):
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/drive_oauth_setup.py --client-file credentials/drive-oauth-client.json
   ```
   זה יוצר `credentials/drive-oauth-token.json` (שם ברירת המחדל) - הקובץ הזה, לא קובץ ה-client, הוא מה שנדרש לריצות הבאות.
8. התקינו את חבילות הפייתון הנדרשות: `pip3 install google-auth requests`.

## דרישות ב-.env

```
GOOGLE_DRIVE_OAUTH_TOKEN_FILE=credentials/drive-oauth-token.json
```

⚠️ **הסקריפט לא טוען את `.env` בעצמו** - הוא קורא את המשתנה מ-`os.environ` בלבד. לכן חובה לטעון את `.env` באותה פקודה, אחרת תתקבל השגיאה "GOOGLE_DRIVE_OAUTH_TOKEN_FILE לא מוגדר או שהקובץ לא נמצא" גם כשהמשתנה כן מוגדר בקובץ והטוקן תקין לגמרי. **כל** הפקודות למטה צריכות את הקידומת הזו:

```bash
set -a; source .env; set +a
```

## פקודות

### 1. בדיקת זהות (לאיזה חשבון זה מאושר)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/drive_upload.py whoami
```

### 2. יצירת תיקייה

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/drive_upload.py create-folder --name "שם התיקייה" --parent <folder_id>
```

`--parent` הוא ה-folder ID של תיקיית האב (מהקישור של Drive, החלק אחרי `/folders/`). בלי `--parent`, התיקייה תיווצר ב-"My Drive" הראשי.

### ⚠️ מרשם התיקיות - קרא לפני שאתה יוצר תיקייה חדשה

הסקיל עובד ב-scope מצומצם (`drive.file`) ולכן **אינו יכול לחפש תיקיות קיימות** - הוא רואה רק מה שהוא עצמו יצר. המשמעות המעשית: אם תריץ `create-folder` בשם שכבר קיים, תיווצר **תיקייה כפולה** במקום שימוש בקיימת. זה קרה בפועל ב-2026-07-28 (נוצרה `dani-outputs` שנייה בשורש הדרייב, אוחדה ידנית).

**לכן: אל תיצור תיקייה בלי לבדוק קודם את הטבלה הזו. אם היעד מופיע כאן, השתמש ב-ID ישירות.**

| תיקייה | Folder ID |
|---|---|
| יעד ברירת מחדל לתוצרים (האב של השאר) | `1rlH6KEr3-IPYdAvzmbGZ4pEjICNeWXXr` |
| `blog` (תיקיית אב למאמרי בלוג) | `1e1RJURjDQ4CeKORmLARc5RWLmSEycK8W` |
| `blog/whatsapp-marketing-avoid-ban` | `1lHmYmu8d1VihSmmAt-yvEybhz_ewQiDr` |
| `blog/manychat-real-examples-small-business` | `1i1_W53vTF3g-oalvWf9LXWiV7P7ztwIu` |
| `blog/5-marketing-automation-mistakes` | `152SIK1UPA71KC5m7EmVP_i07Y1f14AO6` |
| `dani-outputs` | `1WG8O84f-fgQV8TO3ALDkCNGEdSt9pFI4` |
| `dani-outputs/technical-audits` | `1uQ7lKpua4J-nxnBRYvKrZLDW3ktrkblX` |

**מוסכמה למאמר חדש**: תיקייה משלו תחת `blog`, בשם ה-slug של המאמר, ובתוכה ה-`.html`, ה-`.pdf` וחבילת ה-SEO. **כשאתה יוצר תיקייה חדשה - הוסף אותה לטבלה הזו באותו commit**, אחרת הריצה הבאה תשכפל אותה.

### העברת קובץ או תיקייה בין תיקיות

לסקריפט אין פקודת `move`. אם צריך לתקן מיקום (למשל אחרי שנוצרה כפילות), זו קריאת `PATCH` ישירה שמחליפה הורה - **בלי לשכפל את הקובץ**:

```python
requests.patch(f'https://www.googleapis.com/drive/v3/files/{FILE_ID}',
    params={'addParents': NEW_PARENT, 'removeParents': OLD_PARENT, 'fields': 'id,name,parents'},
    headers={'Authorization': 'Bearer ' + creds.token})
```

### 3. העלאת קובץ

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/drive_upload.py upload --file /path/to/image.png --parent <folder_id>
```

אופציונלי: `--name "שם-מותאם.png"` (ברירת מחדל: שם הקובץ המקומי), `--mime-type image/png` (ברירת מחדל: מזוהה אוטומטית מהסיומת).

מחזיר JSON עם `id`, `webViewLink` (הקישור לשיתוף) ו-`size`.

### 4. העברת קובץ לאשפה (לא מחיקה סופית)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/drive_upload.py trash --file-id <file_id>
```

מעביר לאשפה (`trashed: true`) - הפיך, ניתן לשחזור מתוך Drive Trash. אין בסקיל הזה פקודת מחיקה סופית (permanent delete) - בכוונה.

## דוגמת שימוש טיפוסית (מירב, אחרי יצירת תמונה)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/drive_upload.py upload \
  --file merav/outputs/singles/2026-07-26-course-banner.png \
  --parent 1rlH6KEr3-IPYdAvzmbGZ4pEjICNeWXXr
```

## ולידציה ומקרי קצה

- **`GOOGLE_DRIVE_OAUTH_TOKEN_FILE` לא מוגדר/הקובץ לא נמצא** - הסקריפט מחזיר שגיאת JSON ברורה שמפנה להרצת `drive_oauth_setup.py`; הסוכן צריך לדווח שההעלאה לא זמינה ולהמשיך בלי לחסום את שאר המשימה.
- **403 `Service Accounts do not have storage quota`** - סימן שמישהו ניסה לחזור לגישת service account; לא רלוונטי לזרימה הנוכחית, אבל אם מופיע - יש לוודא ש-`GOOGLE_DRIVE_OAUTH_TOKEN_FILE` (לא `GOOGLE_DRIVE_KEY_FILE`) מוגדר.
- **`invalid_grant` בזמן ריענון טוקן** - ה-refresh token בוטל (למשל המשתמשת הסירה את ההרשאה ב-[myaccount.google.com/permissions](https://myaccount.google.com/permissions)) - יש להריץ שוב את `drive_oauth_setup.py`.
- **לא התקבל `refresh_token` בהקמה** - קורה אם האפליקציה כבר אושרה בעבר; יש להסיר את ההרשאה הקיימת ב-[myaccount.google.com/permissions](https://myaccount.google.com/permissions) ולהריץ שוב את ההקמה.
- **שם קובץ כפול** - Drive לא מונע שמות כפולים באותה תיקייה (בשונה ממערכת קבצים רגילה) - כל קריאת `upload` יוצרת קובץ חדש, גם אם השם זהה לקובץ קיים.
- **קבצים גדולים (מעל כמה MB)** - הסקריפט משתמש ב-multipart upload פשוט, מתאים לתמונות/HTML/MD רגילים; לקבצים גדולים מאוד (וידאו וכו') יידרש resumable upload - לא ממומש כאן, לא צורך צפוי בפרויקט הזה.

## תחזוקה

אם בעתיד יידרש גם קריאה/רשימה של קבצים קיימים דרך סקריפט (ולא רק חיבור ה-MCP בשיחה הראשית) - זו תוספת נפרדת לסקריפט הזה (`list`/`get`), לא סקיל נפרד, כי זה אותו אימות ואותו scope.
