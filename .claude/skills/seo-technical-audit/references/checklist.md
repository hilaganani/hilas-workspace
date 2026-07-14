# checklist.md — כל 13 הבדיקות הטכניות

## תוכן עניינים

1. Crawlability
2. Indexability
3. robots.txt
4. Sitemap
5. תגיות Canonical
6. הפניות (Redirects)
7. תוכן כפול
8. נתונים מובנים (Structured Data)
9. Core Web Vitals
10. קישורים שבורים
11. Pagination
12. Hreflang
13. עמודים יתומים

---

## 1. Crawlability

בדוק שדפי המפתח (עמוד הבית, 3-5 מאמרים לדוגמה מה-sitemap) נגישים ב-`WebFetch` בלי חסימה. אם `WebFetch` מחזיר תוכן ריק/שגיאה עקבית — זה איתות (אבל ייתכן גם חסימת בוט ספציפית ל-`WebFetch` ולא ל-Googlebot בפועל, ציין את חוסר הוודאות הזה).

## 2. Indexability

חפש בכל דף שנבדק תגית `<meta name="robots" content="noindex">` — אם קיימת בדף שאמור להיות מדורג, זו בעיה **קריטית**. גם `X-Robots-Tag: noindex` בכותרות ה-HTTP (אם `WebFetch` חושף כותרות — אם לא, ציין שלא ניתן היה לבדוק ברמת ה-header).

## 3. robots.txt

`WebFetch` על `<root>/robots.txt`. בדוק:
- אין `Disallow: /` גורף (חוסם הכל).
- אין חסימה לא-מכוונת של תיקיות תוכן (למשל `/blog/`, `/wp-content/uploads/` אם תמונות נטענות משם).
- יש הפניה ל-sitemap (`Sitemap: ...`) — לא חובה אבל מומלץ.

## 4. Sitemap

`WebFetch` על `<root>/sitemap.xml` או `<root>/sitemap_index.xml`. בדוק:
- הקובץ תקין (XML נטען, לא שגיאת שרת).
- כולל את הדפים שאתם יודעים שקיימים (השווה מדגם מול טבלת "מאגר תוכן קיים" באיירטייבל אם רלוונטי — ראו `seo-internal-linking`).
- תאריכי `<lastmod>` לא כולם זהים/עתיקים באופן חשוד (סימן לסייטמאפ שלא מתעדכן).

## 5. תגיות Canonical

לכל דף מדגמי: יש תגית `<link rel="canonical">`? מצביעה על עצמו (self-referencing) או על גרסה אחרת? קישור canonical ל-URL שגוי (עמוד אחר לגמרי) הוא בעיה **קריטית** — זה יכול לגרום לגוגל להתעלם מהדף.

## 6. הפניות (Redirects)

בדוק דגימת URL-ים ישנים/ידועים (אם יש רשימה) עבור שרשראות הפניה (301 → 301 → 301 במקום 301 יחיד) או הפניות שבורות (302 זמני שנשאר קבוע לאורך זמן, או הפניה ל-404). `WebFetch` לא תמיד חושף קוד סטטוס HTTP במפורש — ציין אם הבדיקה מוגבלת לתוכן הסופי בלבד ולא לשרשרת ההפניות.

## 7. תוכן כפול

השווה כותרות/מטא-תיאורים בין דפים שונים באתר (מתוך ה-sitemap/הטבלה) — כותרות/מטא זהים או כמעט-זהים בין שני דפים שונים הם איתות לתוכן כפול או קניבליזציה של מילות מפתח (שני דפים מתחרים על אותה מילת מפתח בדיוק).

## 8. נתונים מובנים (Structured Data)

חפש בקוד המקור (`WebFetch` עם prompt שמבקש לחלץ תגיות `<script type="application/ld+json">`) סוגי schema קיימים (Article, FAQPage, BreadcrumbList וכו'). ציין אם דף שברור שצריך FAQPage schema (יש בו סקציית שו"ת) לא כולל אותו.

## 9. Core Web Vitals

**דורש `PAGESPEED_API_KEY`** ב-`.env` (חינמי — [console.cloud.google.com](https://console.cloud.google.com), הפעלת "PageSpeed Insights API"). אם קיים:

```bash
curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<PAGE_URL>&key=${PAGESPEED_API_KEY}&strategy=mobile" \
  | jq '.lighthouseResult.audits | {LCP: .["largest-contentful-paint"].displayValue, CLS: .["cumulative-layout-shift"].displayValue, INP: .["interaction-to-next-paint"].displayValue}'
```

הרץ על 2-3 דפים מדגמיים (לא כל הדפים — יש מגבלת קצב על ה-API). אם אין מפתח — דלג לגמרי על הסעיף, ציין בפלט שהוא לא נבדק.

## 10. קישורים שבורים

מתוך תוכן דף מדגמי, חלץ קישורים פנימיים (`WebFetch` עם prompt שמבקש רשימת `href` פנימיים), ובדוק מדגם קטן מהם (`WebFetch` שוב) שהם לא מחזירים שגיאה. זו בדיקה מדגמית בלבד — ציין את זה.

## 11. Pagination

אם באתר יש עמודי ארכיון/רשימה עם pagination (עמוד 1, 2, 3...) — בדוק שיש `rel="next"`/`rel="prev"` (אם עדיין רלוונטי לפורמט האתר) או כל מנגנון pagination-aware אחר, ושכל עמוד pagination לא כולל את אותה תגית canonical של עמוד 1 (זה יגרום לגוגל להתעלם מעמודים 2+).

## 12. Hreflang

**רלוונטי רק אם האתר כולל יותר משפה אחת.** אם האתר בעברית בלבד — ציין "לא רלוונטי", לא "חסר". אם יש כמה גרסאות שפה, בדוק שתגיות `hreflang` מצביעות זו על זו נכון (כולל self-reference).

## 13. עמודים יתומים

ראו `seo-internal-linking` לניתוח מלא — כאן רק ציינו בקצרה אם זוהו עמודים כאלה, עם קישור לדוח המלא של הסקיל הזה.
