---
name: google-analytics
description: מעטפת (wrapper) ל-Google Analytics 4 Data API — נתוני תנועה אמיתיים (סשנים, משתמשים, מקור/מדיום, קמפיין, עמודי נחיתה) לפי טווח תאריכים, ודוח זמן-אמת לאימות שהתג באמת יורה אחרי התקנה. משלים את google-search-console: זה עונה "מאיפה הגיעו ולאן הלכו באתר", וההוא עונה "מה חיפשו בגוגל". דורש GA4_PROPERTY_ID ב-.env וקובץ מפתח של service account (GOOGLE_ANALYTICS_KEY_FILE, ובהיעדרו GOOGLE_SEARCH_CONSOLE_KEY_FILE), ואת חבילות הפייתון google-auth ו-requests. סקיל לקריאה בלבד (read-only) — ה-scope מוגבל ל-analytics.readonly.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ga4_query.py *)
---

# google-analytics — נתוני תנועה אמיתיים מ-GA4

## מטרה והיקף

מאפשר לשלוף נתוני GA4 ישירות לשיחה, במקום שהילה תייצא מסכים ידנית. **קריאה בלבד** — ה-scope הוא `analytics.readonly`, ואין בסקיל שום פעולת כתיבה, שינוי הגדרות, יצירת אירועים או מחיקה.

השאלה המרכזית שהוא נועד לענות עליה: **אילו קמפיינים/מיילים/עמודים באמת הביאו אנשים**, ובאיזה נפח.

## מה הוא לא עושה — קראו לפני שמסיקים מסקנות עסקיות

**GA4 לא יודע מי קנה.** באתר הקורסים לא נשלח אירוע רכישה (`purchase`) — זו הייתה החלטה מכוונת, כדי לא לגעת בתזרים התשלום של SUMIT באמצע השקה חיה. המשמעות:

- GA4 עונה על "כמה אנשים הגיעו, מאיפה, ולאילו עמודים".
- **הרכישות עצמן יושבות בטבלת `orders` בסופאבייס** של פרויקט הקורסים (ראו `courses-platform.md`), ושם סופרים הכנסות.
- חיבור בין השניים ("איזה מייל הביא רוכשים") דורש או אירוע רכישה ב-GA4, או הצלבה ידנית לפי תאריך/קמפיין. אל תדווחו על נתון כזה כאילו הוא מדוד — הוא לא.

בנוסף: המדידה התחילה ב-2026-07-29 ואינה רטרואקטיבית. כל שאלה על תקופה מוקדמת יותר תחזיר ריק, וזה לא אומר "לא הייתה תנועה".

## מבנה המדידה בפועל (חשוב לפרשנות)

שני האתרים — `www.ganani.co.il` (וורדפרס) ו-`courses.ganani.co.il` (Lovable) — מדווחים ל**אותו נכס GA4**, `G-S7E1GGMBGD`, עם מדידה חוצת-דומיינים. זה מכוון: כך מסע של מבקר שהגיע מחיפוש לאתר הראשי ועבר לקורסים נשאר סשן אחד, והמקור המקורי לא נמחק.

לכן:

- **להפרדה בין שני האתרים משתמשים במימד `hostname`**, לא בנכס נפרד:
  `--filter hostname=courses.ganani.co.il`
- **קישורים בין שני האתרים הם קישורים פנימיים ואין עליהם UTM** (הוסר במכוון). אם יופיע פתאום `sessionSource=ganani.co.il` בנפח משמעותי — זה סימן שמדידת הדומיינים ההצלבתית נשברה בהגדרות, לא תובנה שיווקית.

## הקמה חד-פעמית

חשבון השירות הוא **אותו אחד** שכבר משמש את `google-search-console` (`seo-reader@hila-seo.iam.gserviceaccount.com`) — אין צורך ליצור חדש או להוריד מפתח נוסף. שני שלבים:

1. **הרשאה בנכס GA4**: Admin → ניהול גישה לנכס → הוספת המשתמש בהרשאת **צופה** (Viewer), בלי לסמן "יידוע במייל" (זו כתובת של רובוט).
2. **הפעלת שני ממשקי API** בפרויקט הענן `hila-seo`, אחרת כל קריאה תיכשל ב-`SERVICE_DISABLED`:
   - [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com?project=hila-seo) — לדוחות
   - [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com?project=hila-seo) — ל-`list-properties` בלבד

## דרישות ב-.env

```
GA4_PROPERTY_ID=123456789
GOOGLE_ANALYTICS_KEY_FILE=credentials/hila-seo-c04d762108b9.json   # אופציונלי
```

`GA4_PROPERTY_ID` הוא המזהה **המספרי** של הנכס — **לא** מזהה המדידה `G-S7E1GGMBGD`. למצוא אותו: `list-properties` (או Admin → פרטי נכס בממשק GA4).

`GOOGLE_ANALYTICS_KEY_FILE` אופציונלי; בלעדיו הסקריפט נופל חזרה ל-`GOOGLE_SEARCH_CONSOLE_KEY_FILE`, שזה המצב הרגיל כאן.

## פקודות

הסקריפט `scripts/ga4_query.py` **לעולם לא מדפיס את ה-access token** — הוא מטפל באימות פנימית ומחזיר רק נתונים.

### 1. איתור מזהה הנכס

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ga4_query.py list-properties
```

### 2. דוח תנועה

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ga4_query.py report \
  --start-date 2026-08-20 --end-date 2026-08-31 \
  --dimensions sessionSource,sessionMedium,sessionCampaignName \
  --metrics sessions,activeUsers --order-by sessions
```

- `--dimensions` / `--metrics`: שמות ה-API של GA4, מופרדים בפסיקים. שימושיים כאן: `hostname`, `pagePath`, `landingPage`, `sessionSource`, `sessionMedium`, `sessionCampaignName`, `deviceCategory`, `date` · מדדים: `sessions`, `activeUsers`, `screenPageViews`, `userEngagementDuration`, `bounceRate`.
- `--filter dimensionName=value`: סינון בהתאמה מדויקת. השימוש העיקרי — בידוד אתר הקורסים לפי `hostname`.
- `--start-date`/`--end-date` מקבלים גם `NdaysAgo` ו-`today`.

### 3. זמן אמת — לאימות שהתג יורה

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ga4_query.py realtime
```

30 הדקות האחרונות. זו הבדיקה הנכונה מיד אחרי פרסום גרסה חדשה של האתר: פותחים את האתר בדפדפן, מאשרים את באנר העוגיות, ומריצים. אפס משתמשים פעילים אחרי אישור עוגיות = התג לא נטען, ואין טעם להמתין 24 שעות כדי לגלות את זה.

## ולידציה ומקרי קצה

- **`SERVICE_DISABLED` בתשובה** — אחד משני ה-API לא הופעל בפרויקט הענן; הקישור להפעלה מופיע בתוך גוף השגיאה עצמה.
- **`403 PERMISSION_DENIED` בלי `SERVICE_DISABLED`** — חשבון השירות לא נוסף כצופה בנכס, או נוסף לנכס אחר.
- **`GA4_PROPERTY_ID` שגוי** — קל לטעות ולהזין את `G-S7E1GGMBGD`; ה-API דורש את המזהה המספרי ויחזיר שגיאה.
- **דוח ריק** — אין תנועה בטווח, או שהטווח קודם ל-2026-07-29. לדווח כ"אין נתונים לתקופה", לא כ"אין תנועה לאתר".
- **עוגיות** — GA4 נטען באתר הקורסים רק אחרי אישור באנר העוגיות. מבקרים שסירבו אינם נמדדים כלל, ולכן המספרים כאן הם רצפה, לא ספירה מלאה.

## יחס לסקילים אחרים

- **`google-search-console`** — משלים, לא חופף: חיפוש אורגני (מה חיפשו, איפה דורגנו) מול תנועה בפועל באתר. אותו חשבון שירות, scopes ונקודות קצה שונות לגמרי.
- אין תלות בין השניים; כל אחד עובד גם אם השני לא מוגדר.
