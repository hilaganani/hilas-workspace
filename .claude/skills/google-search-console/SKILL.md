---
name: google-search-console
description: מעטפת (wrapper) ל-Google Search Console API — נתוני חיפוש אמיתיים (קליקים, חשיפות, מיקום ממוצע) לפי מילת חיפוש/עמוד/תאריך, בדיקת אינדוקס אמיתית לעמוד ספציפי, ורשימת sitemaps שהוגשו. משמש את דני כדי לשדרג את seo-content-refresh (זיהוי דעיכה אמיתית במקום השערה) ואת seo-technical-audit (אינדקסביליות אמיתית במקום היסק מ-WebFetch). דורש GOOGLE_SEARCH_CONSOLE_KEY_FILE ו-GOOGLE_SEARCH_CONSOLE_SITE_URL מוגדרים ב-.env, ואת חבילות הפייתון google-auth ו-requests. סקיל לקריאה בלבד (read-only) — ה-scope מוגבל ל-webmasters.readonly.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/gsc_query.py *)
---

# google-search-console — נתוני חיפוש אמיתיים מגוגל

## מטרה והיקף

מספק נתוני אמת מ-Google Search Console במקום ההערכות/ההיסקים שדני עושה היום ב-`seo-content-refresh` ו-`seo-technical-audit`. **קריאה בלבד** — אין בסקיל הזה שום פעולת כתיבה/שינוי הגדרות באתר.

## הקדמה חשובה: זה דורש הקמה חד-פעמית, לא רק מפתח API

בניגוד ל-`PAGESPEED_API_KEY` (מפתח שטוח פשוט), Search Console API לא תומך במפתח API רגיל לנתונים פרטיים - הוא דורש **service account** מורשה על ה-property. זו הקמה חד-פעמית של כ-10 דקות:

1. ב-[console.cloud.google.com](https://console.cloud.google.com): צרו פרויקט (או השתמשו בקיים), הפעילו "Google Search Console API".
2. באותו פרויקט: **IAM & Admin → Service Accounts → Create Service Account**. אין צורך להעניק לו תפקידי IAM כלשיהם ברמת הפרויקט - ההרשאה בפועל תינתן בשלב הבא.
3. צרו מפתח JSON לחשבון השירות (**Keys → Add Key → JSON**) והורידו אותו. שמרו אותו **מחוץ לגיט** (למשל `credentials/gsc-service-account.json` - ודאו שהתיקייה הזו ב-`.gitignore`).
4. ב-[search.google.com/search-console](https://search.google.com/search-console): בחרו את ה-property של האתר → **Settings → Users and permissions → Add user**. הוסיפו את כתובת המייל של חשבון השירות (נראית כמו `xxx@project-id.iam.gserviceaccount.com`, מופיעה בקובץ ה-JSON) עם הרשאת **Full** או **Restricted** (Restricted מספיק לקריאה בלבד).
5. התקינו את חבילות הפייתון הנדרשות: `pip3 install google-auth requests`.

## דרישות ב-.env

```
GOOGLE_SEARCH_CONSOLE_KEY_FILE=credentials/gsc-service-account.json
GOOGLE_SEARCH_CONSOLE_SITE_URL=sc-domain:example.com
```

`GOOGLE_SEARCH_CONSOLE_SITE_URL` הוא מזהה ה-property בדיוק כפי שהוא מופיע ב-Search Console - או `sc-domain:example.com` (property ברמת דומיין) או `https://example.com/` (property ברמת URL-prefix, עם ה-`/` הסופי). אם לא בטוחים איזה מהם - זה מופיע בפינה השמאלית העליונה של ממשק Search Console.

## פקודות

הסקריפט `scripts/gsc_query.py` **לעולם לא מדפיס את ה-access token עצמו** - הוא מטפל באימות פנימית ומחזיר רק את נתוני התשובה. שלוש פעולות:

### 1. נתוני חיפוש (clicks/impressions/position)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/gsc_query.py search-analytics \
  --start-date 2026-06-01 --end-date 2026-06-30 \
  --dimensions query,page --row-limit 50
```

- `--dimensions`: כל שילוב מ-`query,page,date,country,device` (מופרד בפסיקים).
- `--url-filter <URL>`: מגביל לעמוד ספציפי בלבד - השימוש המרכזי ב-`seo-content-refresh` (האם המאמר הזה איבד קליקים/מיקום לאורך זמן).
- `--country <קוד>`: מגביל למדינה אחת, בקוד ISO 3166-1 alpha-3 באותיות קטנות (ישראל: `isr`). **זה סינון, לא פילוח** - להבדיל מ-`--dimensions country` שמפרק את התוצאות לפי מדינה ומציג את כולן. שימושי כדי לנקות תנועה לא רלוונטית מחו"ל לפני שמסיקים שמאמר דועך. אפשר לשלב עם `--url-filter`; שני התנאים יחולו יחד.
- **טווח תאריכים מומלץ לזיהוי דעיכה**: הריצו פעמיים - חודש אחרון מול חודש מקביל לפני שנה (או מול 3 החודשים שאחרי הפרסום) - והשוו.

### 2. בדיקת אינדוקס אמיתית לעמוד

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/gsc_query.py inspect --url https://example.com/some-article
```

מחזיר את סטטוס האינדוקס האמיתי (`coverageState`, `indexingState`, `robotsTxtState` ועוד) - זה מחליף את ההיסק העקיף מ-`WebFetch` ב-`seo-technical-audit` סעיף 2 (Indexability).

### 3. רשימת Sitemaps

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/gsc_query.py sitemaps
```

מחזיר את כל ה-sitemaps שהוגשו לגוגל וסטטוס העיבוד שלהם (כולל שגיאות, אם יש) - משלים את הבדיקה הידנית של `sitemap.xml` ב-`seo-technical-audit`.

## איך זה משדרג את הסקילים הקיימים

- **`seo-content-refresh`**: השוואת `search-analytics --url-filter` בין שתי תקופות היא בדיוק הנתון החסר שהסקיל היום מדווח כ"לא זמין" - כשיש גישה, יש להחליף את "מצב מוגבל" בנתון אמיתי, ולציין את זה מפורשות בפלט ("מבוסס נתוני Search Console אמיתיים" במקום "הערכה").
- **`seo-technical-audit`**: `inspect` מחליף את סעיף 2 (Indexability) מהיסק ל-WebFetch לנתון אמיתי; `sitemaps` מוסיף אימות שגוגל בפועל קיבל וקרא את ה-sitemap, לא רק שהוא נגיש.

## ולידציה ומקרי קצה

- **`GOOGLE_SEARCH_CONSOLE_KEY_FILE` לא מוגדר/הקובץ לא נמצא** - הסקריפט מחזיר שגיאת JSON ברורה; דני צריך לדווח שהנתון לא זמין ולחזור להתנהגות הקודמת (הערכה/היסק), **לא** להיכשל בשקט.
- **חשבון השירות לא נוסף כמשתמש ב-Search Console** - הקריאה תיכשל עם `403`; זה סימן שהקמת השלב 4 למעלה לא הושלמה.
- **טווח תאריכים ריק/לא הגיוני** (לפני שהאתר נוסף ל-Search Console) - התשובה תחזור עם `rows` ריק, לא שגיאה - ציינו זאת כ"אין נתונים לתקופה הזו", לא כ"האתר לא מדורג בכלל".
- **`--url-filter`** משתמש בהתאמה מדויקת (`equals`) - ודאו שה-URL זהה בדיוק (כולל `https://` וסלאש סופי אם רלוונטי) לאיך שהוא מופיע ב-sitemap.

## תחזוקה

אם בעתיד יתווסף גם GA4 Data API (נתוני תנועה/המרות, לא רק חיפוש) - זה סקיל נפרד (`google-analytics`), לא הרחבה של זה - השניים משתמשים ב-scopes ובנקודות קצה שונות לגמרי, גם אם אותו service account יכול לשמש את שניהם.
