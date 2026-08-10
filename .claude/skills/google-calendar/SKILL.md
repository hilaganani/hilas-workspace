---
name: google-calendar
description: מעטפת (wrapper) ל-Google Calendar API דרך OAuth אישי — רשימת היומנים של הילה, קריאת אירועים בטווח תאריכים, יצירת אירוע חדש ועדכון אירוע קיים. משמש כשמבקשים "תרשום לי ביומן", "מה יש לי ביום שלישי", "תזיז את הפגישה". דורש GOOGLE_CALENDAR_OAUTH_TOKEN_FILE ב-.env (נוצר ע"י scripts/calendar_oauth_setup.py בהקמה חד-פעמית), ואת חבילות הפייתון google-auth ו-requests. אין בסקיל פעולת מחיקה, במכוון — ביטול אירוע נעשה דרך update-event --status cancelled, שהוא הפיך.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/gcal.py *)
---

# google-calendar — קריאה וכתיבה ליומן של הילה

## מטרה והיקף

מאפשר לרשום ולקרוא אירועים ביומן Google של הילה ישירות מהשיחה, במקום שהיא תפתח את היומן ותקליד בעצמה.

ארבע פעולות בלבד: `list-calendars`, `list-events`, `create-event`, `update-event`.

## מה הוא לא עושה

**אין מחיקה.** לא של אירוע, לא של יומן. מחיקת אירוע היא פעולה הרסנית שקשה לשחזר ממנה, ולכן היא נשארת ידנית ביומן עצמו — באותה רוח ש-`smoove-newsletter` יוצר טיוטה ולא שולח, ו-`airtable-write` יוצר רשומה ולא מעדכן.

לביטול אירוע יש דרך הפיכה: `update-event --status cancelled`. האירוע מסומן כמבוטל ונשאר קיים.

**אין שינוי הגדרות חשבון.** ה-scopes הם `calendar.events` (יצירה/עדכון של אירועים) ו-`calendar.readonly` (רשימת יומנים וקריאה) — שניהם יחד לא מאפשרים למחוק יומן או לגעת בהגדרות.

## הקמה חד-פעמית

1. **להפעיל את Google Calendar API** בפרויקט ה-Google Cloud (אותו פרויקט `hila-seo`):
   [console.cloud.google.com/apis/library/calendar-json.googleapis.com](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com).
   בלי זה כל קריאה נכשלת ב-`SERVICE_DISABLED` — שגיאה שנראית כמו בעיית הרשאות אבל הפתרון שלה אחר לגמרי (אותה מלכודת שמתועדת ב-`google-analytics`). הסקריפט מזהה אותה ומסביר במפורש.

2. **להריץ את זרימת ההרשאה** — נפתח דפדפן, מאשרים, וזהו:

   ```bash
   python3 .claude/skills/google-calendar/scripts/calendar_oauth_setup.py
   ```

   ברירת המחדל משתמשת ב-`credentials/drive-oauth-client.json` הקיים — אותו OAuth client של הדרייב, אותו פרויקט Cloud, אין צורך ליצור חדש.

3. **להוסיף ל-`.env`**:

   ```
   GOOGLE_CALENDAR_OAUTH_TOKEN_FILE=credentials/calendar-oauth-token.json
   GOOGLE_CALENDAR_ID=<מזהה יומן ברירת מחדל>   # אופציונלי
   ```

### למה OAuth ולא service account

ליומן אישי (Gmail רגיל, לא Workspace) חשבון שירות לא יכול לגשת ליומנים של המשתמשת — לשם כך נדרש domain-wide delegation, שקיים רק ב-Google Workspace. זו אותה מסקנה שהתבררה בדרך הקשה ב-`drive-upload`, מסיבה טכנית שונה (שם — היעדר מכסת אחסון).

### למה קובץ טוקן נפרד מזה של הדרייב

לטוקן של הדרייב יש scope של `drive.file` בלבד. הוספת scope של יומן אליו הייתה מחייבת לדרוס טוקן עובד, כלומר לסכן זרימת עבודה חיה בשביל תוספת. שני קבצים נפרדים, אותו client, אפס השפעה הדדית.

## שימוש

### רשימת היומנים

```bash
python3 .claude/skills/google-calendar/scripts/gcal.py list-calendars
```

מחזיר מזהה, שם, הרשאה ואזור זמן לכל יומן. שימושי בפעם הראשונה, כדי לדעת לאיזה יומן לכתוב.

### קריאת אירועים בטווח

```bash
python3 .claude/skills/google-calendar/scripts/gcal.py list-events \
    --calendar "עבודה" --from 2026-08-10 --to 2026-08-17
```

אירועים חוזרים מוחזרים כמופעים בפועל (`singleEvents=true`), לא ככלל חזרה.

### יצירת אירוע

```bash
python3 .claude/skills/google-calendar/scripts/gcal.py create-event \
    --calendar "עבודה" --title "שיחה עם לקוח" \
    --start 2026-08-12T10:00 --end 2026-08-12T11:00 \
    --description "פירוט" --location "זום"
```

- `--end` אופציונלי — בלעדיו האירוע נמשך `--duration` דקות (ברירת מחדל 60).
- אירוע יום-שלם: `--start 2026-08-20 --all-day`. תאריך הסיום של אירוע יום-שלם ב-Google הוא בלעדי, והסקריפט מטפל בזה לבד.
- אזור זמן ברירת מחדל: `Asia/Jerusalem`. לשינוי — `--timezone` לפני שם הפעולה.

### עדכון אירוע

```bash
python3 .claude/skills/google-calendar/scripts/gcal.py update-event \
    --calendar "עבודה" --event-id <id> --start 2026-08-12T14:00 --end 2026-08-12T15:00
```

משתמש ב-`PATCH` ולא ב-`PUT`, כדי ששדות שלא נשלחו יישארו כמו שהם ולא יימחקו בשקט.

## בחירת יומן

`--calendar` מקבל שלושה דברים: מזהה יומן מלא, המילה `primary`, או קטע משם היומן (למשל `"עבודה"`).

התאמה לפי שם נפתרת מול רשימת היומנים האמיתית. אם השם מתאים ליותר מיומן אחד — הסקריפט **עוצר ומציג את המועמדים** במקום לנחש. כתיבה ליומן הלא נכון היא בדיוק סוג הטעות שלא שמים לב אליה עד שמאוחר.

כש-`--calendar` לא נמסר, נעשה שימוש ב-`GOOGLE_CALENDAR_ID` מה-`.env`, ובהיעדרו ב-`primary`.

## אימות

אחרי כל יצירה או עדכון, הסקריפט מדפיס את האירוע כפי שגוגל החזיר אותו — כולל `htmlLink`. זו התשובה של השרת, לא הד של מה שנשלח. אפשר גם להריץ `list-events` על אותו טווח כדי לראות שהאירוע באמת יושב שם.
