---
name: brand-renderer
description: מעטפת גנרית לרינדור טקסט מותג אמיתי (פונטים אמיתיים - Heebo/Assistant, לא ניחוש של מודל תמונה) מעל תמונת קונספט קיימת, דרך HTML/CSS + Playwright. מקבלת קלט מבוסס asset_type (מונח לוגי כמו instagram_quote) ולא שם קובץ/תבנית - לא ייעודי למירב, כל סוכן/יכולת עתידיים יכולים להשתמש בו. קורא צבעים/פונטים מתוך brand/ (מקור אמת משותף), לא מחזיק עותק פרטי. דורש Node + Playwright מותקנים.
---

# brand-renderer — רינדור טקסט מותג אמיתי מעל קונספט ויזואלי

## מתי משתמשים בזה

כשיש כבר תמונת קונספט (רקע/איור/קומפוזיציה - למשל תוצר של מירב מ-`gpt-image-2`, **בלי טקסט**) וצריך להוסיף עליה טקסט אמיתי (כותרת/כיתוב/קרדיט) בפונטים האמיתיים של המותג - **לא** מבקשים ממודל התמונה לצייר את הטקסט בעצמו (מודלי AI לא שולטים בדיוק בטיפוגרפיה עברית - ראו `merav/brand-guidelines.md` §2).

## עקרון: `asset_type`, לא שם תבנית

הקורא (מירב או כל יכולת עתידית) **לא** צריך להכיר שם קובץ HTML, מידות פיקסל, או CSS. הוא בוחר `asset_type` מהקטלוג הבא (שפה עסקית, לא טכנית):

| `asset_type` | מתי להשתמש | Assets נדרשים | שדות תוכן (`content`) |
|---|---|---|---|
| `instagram_quote` | פוסט ריבועי עם ציטוט/משפט מרכזי לפיד | `background` | `headline` (חובה), `caption`, `credit` |
| `instagram_story` | סטורי/כיסוי ריל/TikTok (אנכי) | `background` | `headline` (חובה), `caption`, `credit` |
| `linkedin_banner` | באנר רחב (קאבר פוסט/מאמר לינקדאין) | `background` | `headline` (חובה), `caption`, `credit` |

המיפוי בפועל (איזה קובץ HTML, אילו מידות פיקסל) חי ב-`scripts/catalog.json` - פנימי בלבד, אין צורך לפתוח אותו כדי להשתמש בסקיל. הוספת `asset_type` חדש = שורת קטלוג + קובץ HTML חדש תחת `templates/` - **בלי לשנות את הממשק הזה**.

## דרישות מקדימות

- **Node.js** ו-**Playwright** מותקנים (`npm install playwright && npx playwright install chromium`) - תלות חדשה בפרויקט, לא קיימת בסקילים אחרים (שמבוססי curl/python). ~100MB להורדת Chromium, פעם אחת.
- תיקיית `brand/` בשורש הפרויקט (צבעים, פונטים - ראו `brand/README.md`). **אין לשכפל אותה** - הסקיל קורא ממנה ישירות.

## הרצה

```bash
node .claude/skills/brand-renderer/scripts/render.js --config /path/to/content.json
```

קובץ ה-config הוא JSON:

```json
{
  "asset_type": "instagram_quote",
  "assets": { "background": "/path/to/existing-concept-image.png" },
  "content": {
    "headline": "כותרת ראשית",
    "caption": "כיתוב משני (אופציונלי)",
    "credit": "קרדיט/שם מותג (אופציונלי)"
  },
  "out": "/path/to/final-branded-image.png"
}
```

הפלט: PNG סופי בנתיב `out`, עם הטקסט מרונדר בפונטים האמיתיים (Heebo לכותרות, Assistant לגוף - לפי `brand/tokens.json`) ו-RTL תקין. אין תלות חיצונית - כל התהליך מקומי, שום קובץ לא עולה לאינטרנט.

## טיפול בשגיאות

- **`assets.background` לא קיים** → נכשל מיד עם הודעה ברורה - ודאו שהנתיב לתמונת הקונספט תקין.
- **`asset_type` לא מוכר** → נכשל עם רשימת ה-`asset_type` הזמינים.
- **קובץ פלט בגודל 0 בייטים/חסר** → הסקריפט עצמו בודק זאת ונכשל עם שגיאה מפורשת - לא "מצליח" בשקט (אותו עיקרון כמו `gpt-image-gen`: אל תדווחו הצלחה בלי לוודא בפועל).

## הרחבה

- **`asset_type` חדש** (קרוסלה, כיסוי OG וכו'): שורה חדשה ב-`scripts/catalog.json` (מיפוי ל-template/מידות) + קובץ HTML חדש ב-`templates/`. אפס שינוי במנוע (`render.js`) ואפס שינוי בממשק החיצוני.
- **פונט/צבע נוסף**: מתעדכן ב-`brand/tokens.json` (+ קובץ TTF ב-`brand/fonts/` אם רלוונטי) - זמין מיד לכל התבניות וגם לכל צרכן עתידי אחר של `brand/`.
- **קרוסלה שלמה**: N קריאות עצמאיות לסקיל הזה (אחת לכל שקף), בדיוק כמו ש-N קריאות ל-`gpt-image-2` כבר קורות היום לקרוסלה - אין "מצב multi-slide" מיוחד.
