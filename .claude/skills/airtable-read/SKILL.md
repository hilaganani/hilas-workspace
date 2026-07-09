---
name: airtable-read
description: מעטפת (wrapper) לקריאה בלבד (read-only) מכל טבלה בבייס Airtable של המשתמשת, דרך ה-REST API הרשמי. משמש בעיקר את יעל (Yael), היועצת האסטרטגית, כדי לראות טבלאות תכנון/תוכן/עסקיות לפני בניית תוכנית תוכן חודשית או בדיקת נושא. דורש AIRTABLE_API_KEY ו-AIRTABLE_BASE_ID מוגדרים ב-.env. סקיל לקריאה בלבד — אין בו שום פעולת כתיבה/עדכון/מחיקה.
---

# airtable-read — קריאת רשומות מכל טבלה בבייס

## עקרון מפתח: קריאה בלבד, מכל טבלה בבייס

הסקיל הזה **קורא רשומות בלבד**, מכל טבלה בבייס שה-token מורשה אליו — לא רק טבלה אחת קבועה. אין בו שום קריאת `POST`/`PATCH`/`PUT`/`DELETE` ל-Airtable, ואסור להוסיף כזו. אם יש צורך עתידי בכתיבה לאיירטייבל — זה סקיל נפרד, החלטה נפרדת, לא הרחבה של הסקיל הזה.

## דרישות מקדימות

ב-`.env` בשורש הפרויקט:
- `AIRTABLE_API_KEY` — Personal Access Token מ-[airtable.com/create/tokens](https://airtable.com/create/tokens), עם scope `data.records:read` (וכדאי גם `schema.bases:read`, כדי לרענן את רשימת הטבלאות בהמשך אם היא משתנה), מוגבל (scoped) לבייס הרלוונטי — **על כל הטבלאות בבייס**, לא טבלה בודדת.
- `AIRTABLE_BASE_ID` — מזהה הבייס (מתחיל ב-`app...`), מופיע בכתובת ה-URL של הבייס באיירטייבל.

## הטבלאות הידועות בבייס הזה (עודכן לאחרונה ב-2026-07-09)

| טבלה | Table ID | שימוש עיקרי ליעל |
|---|---|---|
| מאגר תוכן קיים | `tbl1eG92lW0vsY0tc` | כל פוסטי הבלוג שכבר פורסמו — להימנע מכפילות נושאים |
| מאגר תוכן - ניוזלטר | `tbl4SMIJjdjhdtkMl` | ארכיון ניוזלטרים שכבר נשלחו |
| תכנון תוכן חודשי | `tbl6S09qb9wK2ARW6` | תוכנית/יומן תוכן חודשי קיים — לבדוק לפני בניית תוכנית חדשה |
| תוכנית כלכלית חדש | `tbl2qOR40DFJYMZF0` | רעיונות מוצרים דיגיטליים חיים (ראו גם `yael/strategy.md` סעיף 5) |
| תוכנית כלכלית חודשית - ישן | `tbl0hcLngIcokpwwH` | גרסה ישנה — כנראה לא רלוונטי, לבדוק מול המשתמשת/רועי לפני הסתמכות |
| תוכנית שיווקית | `tblHIqGsRbnpUYMtZ` | תוכנית שיווקית כללית |
| נושאים | `tblvnN3dFvABC1bmG` | רעיונות/נושאים לתוכן |
| היילייטים אינסטגרם | `tbl0Fv7YIOBk6FpUk` | תוכן להיילייטים באינסטגרם |
| משימות | `tblMv0wIelhL8sttP` | משימות צוות (בעיקר תפעולי, פחות אסטרטגי) |
| סטטוס לקוחות | `tblbTtrb8jFtQSWs7` | מצב לקוחות קיימים |
| למנכל | `tbl2tw3k7KO4eRJBD` | הערות/הודעות לרועי (המנכ"ל) |

**שימו לב:** שמות הטבלאות עלולים להשתנות (המשתמשת יכולה לשנות שם טבלה באיירטייבל). ה-**Table ID** (מתחיל ב-`tbl...`) יציב ולא משתנה — עדיפות תמיד לשימוש ב-ID בקריאות בפועל. אם קריאה נכשלת ב-`404` וחושדים ששם/ID השתנו — רעננו את הרשימה עם הקריאה הבאה.

## ריענון רשימת הטבלאות (Metadata API)

```bash
curl -s "https://api.airtable.com/v0/meta/bases/$AIRTABLE_BASE_ID/tables" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" | jq -r '.tables[] | "\(.name)  (id: \(.id))"'
```

דורש scope `schema.bases:read` בטוקן. אם נכשל עם `403` — ייתכן שה-token לא כולל את ה-scope הזה; עדיין אפשר לקרוא רשומות מטבלה ספציפית לפי ה-ID הידוע מהטבלה למעלה גם בלי scope זה.

## הקריאה הבסיסית לרשומות מטבלה (לפי Table ID — מומלץ)

```bash
curl -s -G "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/<TABLE_ID>" \
  --data-urlencode "pageSize=100" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" | jq .
```

(אפשר גם שם טבלה בעברית במקום ID, אבל אז צריך URL-encoding: `$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "מאגר תוכן קיים")`.)

## סינון ושליפה חלקית (מומלץ כדי לא להציף בהקשר מיותר)

```bash
curl -s -G "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/<TABLE_ID>" \
  --data-urlencode "fields[]=נושא" \
  --data-urlencode "fields[]=פלטפורמה" \
  --data-urlencode "fields[]=סטטוס" \
  --data-urlencode "fields[]=תאריך יעד" \
  --data-urlencode "maxRecords=50" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" | jq '.records[] | {id, fields}'
```

התאימי את שמות ה-`fields[]` לעמודות בפועל באותה טבלה — הריצי פעם ראשונה בלי סינון `fields` כדי לראות אילו עמודות קיימות בה (העמודות שונות מטבלה לטבלה).

## פאג'ינציה

Airtable מחזיר עד 100 רשומות לקריאה, עם `offset` בתגובה אם יש עוד:

```bash
curl -s -G "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/<TABLE_ID>" \
  --data-urlencode "offset=<the-offset-from-previous-response>" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" | jq .
```

## טיפול בשגיאות

- **`401`/`403`** — כמעט תמיד `AIRTABLE_API_KEY` שגוי/פג תוקף, או שה-scope של ה-token לא כולל את הטבלה/הרשאת `data.records:read`. לא בעיה בשם/ID הטבלה.
- **`404`** — `AIRTABLE_BASE_ID` או ה-Table ID שגויים, או שהטבלה נמחקה. רעננו את רשימת הטבלאות (Metadata API למעלה) לפני שמניחים תקלה אחרת.
- **תגובת JSON בלי שדה `records`** — סימן לשגיאת API; הדפיסי את כל גוף התגובה כדי לאבחן במקום להניח.

## לא לשלוף הכל תמיד

יש כאן 11 טבלאות עם מטרות שונות. לרוב משימה נתונה רלוונטיות רק 1-3 מהן (למשל: בניית תוכנית חודשית → `תכנון תוכן חודשי` + `מאגר תוכן קיים`; בדיקת נושא לקורס דיגיטלי → `תוכנית כלכלית חדש`). אין צורך/טעם לקרוא את כל 11 הטבלאות בכל משימה — זה מציף הקשר לשווא ומאט את העבודה.
