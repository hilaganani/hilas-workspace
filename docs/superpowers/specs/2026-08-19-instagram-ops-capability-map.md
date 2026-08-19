# Instagram Ops — Capability Map

| Capability | Status | Dependency | מה עובד בפועל / Gap |
|---|---|---|---|
| קריאת Google Sheet | available now when connector is connected | Google Drive/Sheets connection | קורא את `תוכן ותפעול` ואת `ביצועים` כמקור האמת התפעולי |
| עדכון Google Sheet | available for approved factual operations | Google Drive/Sheets connection וה-workflow המאושר | עדכון ממוקד של עובדות בלבד; ללא שינוי schema או החלטות תוכן |
| קריאת Instagram Insights | requires setup | Chrome/session מחובר שמסופק בזמן הריצה, או export/screenshots | אין ב-repository כלי Chrome ייעודי מובטח; ללא גישה מדווחים gap |
| קריאת Search Console | available when configured | `google-search-console`, `Bash`, service-account key ו-property מקומיים | read-only; Platform Property חייבת להיות מורשית ומוגדרת במפורש |
| שמירת snapshots | available when evidence and Sheets access exist | גיליון `ביצועים` | append-only; כל מדידה היא שורה חדשה, וערך חסר נשאר ריק |
| עדכון `current-state.md` | available now | `Read`/`Edit`, repository עדכני | מותר רק בחלקים התפעוליים; אסור לשנות אסטרטגיה או תוכן מאושר |
| performance report | available now | Evidence נגיש מקובץ, API read-only, URL או screenshot/export | Facts/Missing data/Anomalies/No interpretation |
| עבודה ממחשב אחר | requires setup | Git clone/pull, secrets מקומיים, גישה למקורות משותפים | persona ו-current-state tracked; קבצים מקומיים בלבד אינם ניידים |
| ניהול secrets | forbidden in Git; local setup required | `.env`/`credentials` מוחרגים מ-Git | אסור להציג, להדפיס, להעתיק לדוח או להתחייב ל-Git |
| כתיבת תוכן/אסטרטגיה | forbidden | ללא | Ops אינו סוכן תוכן ואינו מחליף את גפן |
| פרסום | forbidden by default | הוראה מפורשת וכלי ייעודי עתידי | אין כיום כלי פרסום מוגדר |
| שינוי schema | forbidden without approval | אישור הילה | אין להוסיף/לשנות גיליונות, עמודות או ערכי בחירה |

## ממשק לגפן

Ops מוסר Evidence במבנה: `Scope → Facts → Missing data → Anomalies → No interpretation`. גפן בלבד מפרשת את המשמעות לתוכן, Hook, נושא, ניסוי או המחזור הבא.
