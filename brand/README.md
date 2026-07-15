# brand/ — מקור אמת מרכזי לנכסי המותג

תיקייה משותפת, לא ייעודית לאף סוכן/סקיל ספציפי. `.claude/skills/brand-renderer/` קורא ממנה בזמן ריצה, וכל יכולת עתידית אחרת (למשל מחולל PDF/דוחות/מצגות) יכולה לעשות זאת גם היא - בלי להחזיק עותק פרטי משלה.

## מה יש כאן

- **`tokens.json`** - פלטת הצבעים, שמות משפחות הגופנים, יחס-ממדים ונתיבי הלוגו, וכללי RTL בסיסיים. **תמלול מכני ידני** של `merav/brand-guidelines.md` (§1 צבעים, §2 טיפוגרפיה, §3 לוגו) - לא נוצר אוטומטית.
- **`fonts/`** - קובצי Heebo/Assistant **סטטיים** (Regular+Bold, לא variable font - ראו הערה למטה).

## מה **לא** נמצא כאן (בכוונה)

- **קובצי הלוגו עצמם** - נשארים במקור היחיד הקיים, `merav/reference/logo/` (`hila-ganani-logo-black.png` / `hila-ganani-logo-white.png`), כי מירב כבר תלויה בנתיב הזה לצורך image-edit compositing. `tokens.json` רק מצביע לשם, לא משכפל.

## מניעת דריפט

אם `merav/brand-guidelines.md` מתעדכן (צבע חדש, שינוי גופן וכו') - **יש לעדכן את `tokens.json` באופן ידני בהתאם**. אין כרגע סקריפט שמפרסר את ה-md אוטומטית (שיפור עתידי אפשרי, לא v1).

## למה קבצי גופן סטטיים ולא ה-variable font המקורי

Heebo/Assistant מ-Google Fonts מגיעים כ-variable font יחיד (כל המשקלים בקובץ אחד). לצורך שימוש עקבי ב-`@font-face` (ואפשרי embedding עתידי בפורמטים אחרים), הופקו כאן מופעים **סטטיים** (Regular/Bold בלבד) בעזרת `fonttools varLib.instancer --update-name-table`, עם שמות family/subfamily תקינים (`Heebo`/`Regular`/`Bold`, `Assistant`/`Regular`/`Bold`) ודגלי bold תקינים ב-OS/2/head.
