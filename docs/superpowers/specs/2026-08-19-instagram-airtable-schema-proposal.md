# Instagram Airtable Schema v1 — Superseded

> **Superseded on 2026-08-19.** הילה החליטה שהתשתית התפעולית של Instagram תנוהל ב-Google Sheets ובממשק עברי. מסמך זה נשמר כהיסטוריית החלטה בלבד ואינו בסיס ליישום. ההצעה הפעילה נמצאת ב-`2026-08-19-instagram-google-sheets-schema-proposal.md`.

> תכנון בלבד. אין ליצור טבלאות, שדות, Views, Automations או רשומות לפני אישור הילה.

## עקרונות v1

- Airtable מחזיק מצב תפעולי ועובדות גולמיות בלבד.
- אין Content Bank, Experiments או Highlights נוספים.
- Gefen מחשבת ratios ומפרשת Evidence בזמן report; Airtable אינו שכבת analysis.
- שדה מספרי חסר נשאר `null`. `--` אינו `0`.
- הרשאות הסוכנים הן contract ברמת persona/workflow, לא Airtable field permissions.

# Instagram Operations v1

| Field | Type | Why it survives |
|---|---|---|
| Working Title | Single line text (primary) | השם האנושי של כל חומר גלם, רעיון או תוצר; מונע primary formula נוסף |
| Content ID | Single line text | מזהה קבוע וייחודי מרגע שהפריט הופך ל`תוכן`; נדרש ל-handoffs, קבצים, Insights והתאמה ללוח החודשי |
| Record Type | Single select | הדרך היחידה להחזיק באותה טבלה `חומר גלם`, `רעיון` ו`תוכן` בלי Content Bank נפרד |
| Pillar | Single select | Gefen צריכה לשייך ולנתח תוכן מול 15 נושאי-האב; מותר ריק לחומר גלם לא מסווג |
| Format | Single select | נדרש לכתיבה, עיצוב, ביצוע והשוואת ביצועים; מותר ריק עד שהרעיון נכנס להפקה |
| Hook | Long text | רכיב קריאייטיבי מרכזי שמועבר מגפן ל-Ops ונדרש ללמידה לאחר פרסום |
| Notes / Source Material | Long text | מאחד חומר גלם, context עסקי, blocker, Reference Learning והערות תפעוליות קצרות |
| Reference URL | URL | תומך ב-Reference Analysis בלי להעתיק את יצירת המקור; נשאר כי זה שימוש workflow מפורש |
| Approved Output | URL | אינדקס לנוסח המאושר ב-Git/Drive/מקור משותף; Airtable אינו מעתיק את הטקסט |
| Final Asset | URL | נדרש בנפרד מהטקסט המאושר כאשר יש עיצוב/וידאו/קרוסלה סופיים |
| Target Date | Date | מועד העבודה הפעיל של Ops וקביעת הפרסום הבא |
| Workflow Status | Single select | מתאר היכן הפריט נמצא במחזור באמצעות שישה ערכים בלבד |
| Required Action | Single select | מתאר מה צריך לקרות עכשיו ומאפשר View `ממתין להילה` בלי לפצל את הסטטוסים |
| Live URL | URL | Evidence מרכזי לכך שהתוכן פורסם ומפתח לאיסוף Insights |
| Published At | Date with time | זמן הפרסום האמיתי; נדרש לחישוב גיל snapshot בדוח |
| Highlight Instruction | Single select | שדה יחיד שמתעד לא לשמור, לשמור לקטגוריה או שכבר נשמר |
| Experiment | Single line text | מזהה + השערה קצרה למחזור הניסויים הראשון, בלי טבלה נפרדת |

**סה"כ: 17 שדות.**

## Select values

### Record Type

- `חומר גלם`
- `רעיון`
- `תוכן`

### Workflow Status

- `מאגר`
- `מאושר לכתיבה`
- `בביצוע`
- `מוכן לפרסום`
- `פורסם`
- `לא עלה`

### Required Action

- `אישור הילה`
- `מידע מהילה`
- `כתיבה`
- `צילום`
- `עיצוב`
- `פרסום`
- `איסוף נתונים`

שני השדות נשארים: Status מאפשר תמונת מצב יציבה; Required Action מאפשר לדעת מי/מה מעכב בלי לייצר סטטוס נפרד לכל פעולה. פירוט החסם עצמו נשמר ב-`Notes / Source Material`, ולכן `Blocker` נפרד הוסר.

### Format

- `Reel`
- `Carousel`
- `Stories`
- `Static Post`

### Pillar

15 הערכים נשארים זהים ל-`instagram/content-pillars.md`; אין ליצור אותם מחדש ממקור אחר.

### Highlight Instruction

- `לא לשמור`
- `לשמירה | מתחילים כאן`
- `לשמירה | מהשטח`
- `לשמירה | תוצאות`
- `לשמירה | שיווק`
- `לשמירה | מאחורי הקלעים`
- `נשמר | מתחילים כאן`
- `נשמר | מהשטח`
- `נשמר | תוצאות`
- `נשמר | שיווק`
- `נשמר | מאחורי הקלעים`

## Monthly Plan recommendation

`Monthly Plan Record` הוסר.

Ops מאתר את רשומת `תכנון תוכן חודשי` לפי **Content ID שמופיע באופן מפורש בנושא/הערה של רשומת העל**. עדכון מותר רק אם נמצאה התאמה יחידה. אם אין התאמה או שיש יותר מאחת, Ops מדווח על ambiguity ועוצר במקום לנחש.

כלל מקור האמת:

- Operations: Target Date, status מפורט, Live URL וכל פרטי Instagram.
- תכנון תוכן חודשי: projection רב-ערוצי בלבד.
- כלי הכתיבה העתידי יעדכן באותה פעולה את summary הקיים בטבלת העל; הילה לא תתחזק כפילות ידנית.

## Views מוצעים

1. `ביצוע עכשיו`
2. `ממתין להילה`
3. `פורסם`
4. `רעיונות וחומרי גלם`

# Instagram Insights v1

| Field | Type | Why it survives |
|---|---|---|
| Snapshot ID | Auto number (primary) | מזהה פשוט ל-snapshot בלי primary formula או שדות עזר |
| Operation | Linked record → Instagram Operations | הקשר המחייב בין snapshot לפרסום אחד; Content ID מתקבל דרך הרשומה המקושרת |
| Snapshot At | Date with time | הזמן המדויק שבו המדדים נקראו |
| Source | Single select | מבחין בין נתון UI חי, פרופיל או export/screenshot |
| Views | Number (integer) | מדד החשיפה המרכזי שמופיע בפועל ברוב התכנים |
| Reach | Number (integer) | בסיס להשוואת תפוצה ואפשרות לחישובי ratios בדוח |
| Non-follower % | Percent | שומר breakdown ללא-עוקבים כאשר Instagram מציג אותו כאחוז; אין שדה count נוסף |
| Likes | Number (integer) | אינטראקציה בסיסית זמינה |
| Comments | Number (integer) | אינטראקציה עמוקה יחסית ונדרשת ליעדי תגובות |
| Saves | Number (integer) | מדד מרכזי לתוכן Reference/Checklist וליעד שמירות |
| Shares | Number (integer) | מדד מרכזי להפצה אורגנית |
| Profile Visits | Number (integer) | פעולה עמוקה יותר מ-Reach כאשר מיוחסת לפוסט |
| Follows | Number (integer) | תוצאה ברמת צמיחת החשבון כאשר Instagram מציג attribution |
| Average Watch Time | Duration | מדד צפייה יחיד ל-Reels; Total Watch Time ו-Retention נדחים עד שיוכח שהם זמינים ועקביים |
| Missing Data Note | Long text | מתעד `--`, מדד שלא הוצג, attribution לא ברור או מגבלת מקור בלי להכניס אפס |

**סה"כ: 15 שדות.**

## Source values

- `Instagram Insights`
- `Instagram Profile`
- `Hila Export / Screenshot`

## Non-follower rule

v1 שומר רק percentage. אם המקור מציג count בלבד, Ops אינו ממיר אותו לאחוז ואינו מנחש; הוא מציין זאת ב-`Missing Data Note`. אם count יחזור כמקור עקבי ושימושי בכמה מחזורי מדידה, ניתן להחליף או להוסיף שדה ב-v2.

## Raw facts → report calculations

אין formulas ב-Insights v1.

בזמן performance report, Ops/Gefen מחשבים לפי הצורך:

```text
Measurement Age Hours = Snapshot At - Operation.Published At
Save Rate = Saves / Reach
Share Rate = Shares / Reach
Profile Visit Rate = Profile Visits / Reach
```

כל יחס מחושב רק כאשר שני הערכים קיימים ו-Reach גדול מאפס. החישוב מציין את חלון המדידה ואינו נשמר חזרה ל-Airtable.

החלטה זו משאירה ב-Airtable עובדות גולמיות ומונעת שדות formula שאינם משמשים כרגע ל-View או למיון שוטף.

## Measurement timing

כל מדידה היא row חדש. Ops מחשב בדוח את גיל המדידה כדי לזהות snapshots סביב 24 שעות, 7 ימים ו-30 ימים. אין שדות cadence או עמודות `views_24h`/`views_7d`/`views_30d`.

## Views מוצעים

1. `Snapshots by Content` — קיבוץ לפי Operation ומיון לפי Snapshot At.
2. `Missing Data` — Missing Data Note אינו ריק.

# מה השתנה מגרסת 23/22

## הוסר מ-Operations

- `Item` formula — Working Title הוא ה-primary.
- `Reference Learning` — אוחד ל-Notes / Source Material.
- `Blocker` — אוחד ל-Notes / Source Material; Required Action נשאר הסיווג.
- `Business Context` — אוחד ל-Notes / Source Material.
- `Monthly Plan Record` — התאמה קשיחה לפי Content ID; ambiguity חוסם עדכון.
- `Insights` כשדה מתוכנן ידנית — ייווצר אוטומטית כ-inverse כאשר טבלת Insights תקושר.

## אוחד או שונה

- `Source Material` הפך ל-`Notes / Source Material` ומחזיק חומר גלם, context, blocker ו-learning קצר.
- `Approved Copy URL` קוצר ל-`Approved Output`.
- `Final Asset URL` קוצר ל-`Final Asset`.
- Approved Output ו-Final Asset נשארו נפרדים כי טקסט מאושר ונכס ביצועי אינם תמיד אותו קובץ או אותה תיקייה.

## הוסר מ-Insights

- `Snapshot` formula — הוחלף ב-Auto number.
- `Published At` rollup.
- `Measurement Age Hours` formula.
- `Total Watch Time`.
- `Retention %`.
- `Save Rate`, `Share Rate`, `Profile Visit Rate` formulas.

## נדחה בכוונה ל-v2

- שדה Non-follower count נוסף.
- Total Watch Time, Retention curve ו-Completion Rate.
- ratios שמורים ו-Views שממוינים לפיהם.
- Campaign/Product/Launch fields נפרדים.
- טבלת Experiments וקשרים אליה.
- מבנה Reference עשיר או ספריית Inspiration נפרדת.
- מדדי GSC/GA4 בתוך Insights.
- Linked Record ישיר ל`תכנון תוכן חודשי`.

# הרשאות v1 בקצרה

- Hila: full access.
- Instagram Ops: כתיבה תפעולית ו-Evidence בלבד, לאחר אישור כלי כתיבה מוגבל.
- Gefen: read-only ב-Airtable; מוסרת החלטות דרך workflow.
- Merav: מוסרת Final Asset ל-Ops, ללא צורך בכתיבה ישירה.
- Yael: read-only לפי צורך עסקי.

# המלצה סופית

- **Instagram Operations v1: 17 שדות.**
- **Instagram Insights v1: 15 שדות.**
- אין formulas ב-Insights v1; ratios וגיל snapshot מחושבים בדוח.
- לא ליצור עדיין Automation, Content Bank, Experiments table, Highlights table או שדות עתידיים.
