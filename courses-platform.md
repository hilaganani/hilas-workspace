# אתר הקורסים — מסמך התמצאות

אתר הקורסים **אינו** חלק מהתיקייה הזו. הוא פרויקט Lovable נפרד. הקובץ הזה קיים כדי שלא יהיה צורך לשאול את הילה שוב איפה דברים נמצאים — הוא לא מתעד את המערכת, הוא מפנה לתיעוד שלה.

## זהות הפרויקט

| | |
|---|---|
| שם ב-Lovable | `gananicourses` ("Course Connect Hub") |
| Project ID | `28be939f-66fe-4dbb-8b88-fbebbaa74151` |
| Workspace | `SDhpfFncRNZhwHGbc7jS` ("Hila's Lovable") |
| כתובת בפרודקשן | `https://courses.ganani.co.il` |
| כתובת Lovable | `https://gananicourses.lovable.app` |
| Stack | TanStack Start (TypeScript) + Supabase |

גישה לקוד מהשיחה הזו: דרך ה-MCP של Lovable (`read_file` / `list_files` עם ה-Project ID למעלה). אין עותק מקומי.

## סליקה: SUMIT

**ספק הסליקה הוא SUMIT.** התזרים המלא, כולל הבאג ההיסטורי שתוקן והארכיטקטורה הנוכחית, מתועד ב-`docs/purchase-flow.md` **בתוך פרויקט הקורסים** — זה מקור האמת, לא הקובץ הזה.

תמצית, לצורך התמצאות בלבד:

1. SUMIT מפנה את הקונה ל-`/api/public/sumit/return`
2. הנקודה קוראת ל-`finalizeOrder` ב-`src/lib/sumit.server.ts`
3. `finalizeOrder` מאמת את התשלום מול SUMIT server-to-server
4. אם אומת, רץ רצף קבוע: `ensureOrderUser` (יצירת משתמש) → `enrollPaidOrder` (הרשמה לקורס) → `sendWelcomeEmailIfNeeded` (מייל ברוכים הבאים דרך Resend)

יצירת הגישה קורית **בצד השרת**, לא בדפדפן — זה תוקן במכוון אחרי שקונים נשארו בלי גישה כשהדפדפן נסגר. אין לחזור לתלות בצד הלקוח.

קבצים מרכזיים: `src/lib/sumit.server.ts` · `src/lib/payments.functions.ts` · `src/lib/welcome-email.server.ts` · `src/routes/checkout.tsx`

## נקודות חיבור לאוטומציה

טבלת `orders` ב-Supabase היא המקום הנכון להאזין לרכישות. **עדיף על נגיעה בקוד תזרים התשלום**, שנבדק end-to-end ואין סיבה לסכן אותו.

**קיים כבר (28.7.2026):** הטריגר `trg_notify_make_order_paid` על `public.orders` שולח webhook ל-Make בכל מעבר `pending → paid`, ומשם הרוכש נכנס לרשימת "רוכשים 7 יסודות" בסמוב. הפירוט המלא — כולל המזהים, מה נבדק ומה לא, והמגבלה שאין בו סינון לפי קורס — ב-[`launch-7-yesodot.md`](launch-7-yesodot.md) §7. **אוטומציה נוספת על רכישות צריכה להתחבר לאותו טריגר, לא ליצור מנגנון מקביל.**

הערה טכנית: `pg_net` הותקן ב-28.7.2026 לצורך הטריגר הזה (`net.http_post`). קודם לכן לא היה מותקן.

## מוצרים

| קורס | מחיר | כתובת |
|---|---|---|
| 7 יסודות שכל עסק צריך כדי לשווק את עצמו | 99 ₪ (מעוגן מול 279) · עולה ל-129 ב-11.9.2026 | `/course/7-marketing-foundations` |

9 שיעורי וידאו. **השיעור הראשון פתוח לצפייה חינם בדף המכירה, בלי הרשמה ובלי כרטיס אשראי.** ביטול תוך 14 יום כל עוד לא נצפו שיעורים.

## מה עוד יש ב-Lovable

- `one-on-one-meetings-hila-ganani` — דף פגישת ייעוץ (`b3705fe9-8e3d-457a-8fb0-7fe2fb661874`)
- `מסע הלקוח המוזהב` — תרשים זרימה, לא מפורסם (`c78ba64f-690e-4b05-af44-9713f34796cf`)
