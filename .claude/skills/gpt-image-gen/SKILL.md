---
name: gpt-image-gen
description: מעטפת (wrapper) לקריאת ה-OpenAI Images API עם מודל gpt-image-2, ליצירת תמונה מ-prompt טקסטואלי. משמש בעיקר את מירב (Merav), מייצרת התמונות של הצוות. דורש OPENAI_API_KEY מוגדר ב-.env.
---

# gpt-image-gen — יצירת תמונה דרך OpenAI Images API

## מודל

**`gpt-image-2`** — מודל אמיתי וקיים של OpenAI, יצא ב-21 באפריל 2026, זמין דרך ה-Images API הרגיל (`/v1/images/generations`) וגם דרך ה-Responses API.

⚠️ **אין לשנות את שם המודל.** אל תחליפי אותו ב-`dall-e-3`, `gpt-image-1`, או כל שם אחר — גם אם הוא לא מוכר לך. אם קריאת ה-API נכשלת, הסיבה כמעט תמיד היא **מפתח API שגוי/חסר** או **פרמטר שגוי בבקשה** — לא שם המודל.

## דרישות מקדימות

- `OPENAI_API_KEY` מוגדר ב-`.env` בשורש הפרויקט.
- ייתכן שיידרש **אימות ארגוני (Organization Verification)** בחשבון ה-OpenAI כדי להשתמש במודלי GPT Image — אם הקריאה נכשלת עם שגיאת הרשאה, זו סיבה אפשרית.

## הקריאה הבסיסית (עם jq — אם מותקן)

```bash
curl -s -X POST "https://api.openai.com/v1/images/generations" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "<the prompt>",
    "size": "1024x1024",
    "quality": "medium",
    "output_format": "png"
  }' | jq -r '.data[0].b64_json' | base64 --decode > "<output-path>.png"
```

מודלי GPT Image (בניגוד ל-DALL·E) **תמיד** מחזירים את התמונה כ-base64 ב-`data[0].b64_json` — אין צורך לציין `response_format`.

## Fallback #1 — PowerShell (מאומת עובד; מומלץ ב-Git Bash על Windows)

⚠️ **חשוב, מתוך ניסיון בפועל:** על חלק ממחשבי Windows, `python3`/`python` הן רק "App Execution Alias" סתומות של Microsoft Store (מריצות רק כניסיון לפתוח את החנות) ולא Python אמיתי — גם אם `which python3` מוצא אותן ב-PATH. **בדקי בפועל לפני שאת סומכת על ה-fallback של Python** (סעיף הבא). אם יש ספק, ה-fallback הבא (PowerShell) מאומת עובד ונקרא ישירות מתוך Bash, גם ב-Git Bash:

```bash
curl -s -X POST "https://api.openai.com/v1/images/generations" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "<the prompt>",
    "size": "1024x1024",
    "quality": "medium",
    "output_format": "png"
  }' > /tmp/gpt-image-response.json

powershell.exe -NoProfile -Command '
$resp = Get-Content -Raw "<windows-path-to-tmp>\gpt-image-response.json" | ConvertFrom-Json
if ($resp.error) { Write-Output "API ERROR:"; $resp.error | ConvertTo-Json; exit 1 }
$bytes = [Convert]::FromBase64String($resp.data[0].b64_json)
[System.IO.File]::WriteAllBytes("<windows-output-path>.png", $bytes)
Write-Output "Size: $((Get-Item "<windows-output-path>.png").Length)"
'
```

- ב-Git Bash, `/tmp` בדרך כלל ממופה ל-`C:\Users\<user>\AppData\Local\Temp` — תצטרכי את הנתיב בפורמט Windows (לא `/tmp/...`) בתוך פקודת ה-PowerShell.
- זה **הוכח בפועל** (נבדק ב-2026-07-07): קריאה אמיתית ל-`gpt-image-2`, פענוח base64, ושמירת PNG תקין בגודל 808,203 בייטים — ראו `merav/outputs/2026-07-07-test-lightbulb-icon.png`.

## Fallback #2 — Python (רק אם וידאת ש-Python אמיתי מותקן)

```bash
python3 --version   # ודאי שזו לא הודעת שגיאה/פתיחת Microsoft Store לפני שסומכים על זה
```

אם `python3 --version` מחזיר גרסה אמיתית (למשל `Python 3.11.4`):

```bash
curl -s -X POST "https://api.openai.com/v1/images/generations" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "<the prompt>",
    "size": "1024x1024",
    "quality": "medium",
    "output_format": "png"
  }' > /tmp/gpt-image-response.json

python3 -c "
import json, base64, sys
with open('/tmp/gpt-image-response.json') as f:
    resp = json.load(f)
if 'data' not in resp or not resp['data']:
    print('ERROR from API:', json.dumps(resp), file=sys.stderr)
    sys.exit(1)
b64 = resp['data'][0]['b64_json']
with open('<output-path>.png', 'wb') as out:
    out.write(base64.b64decode(b64))
"
```

## פרמטרים נתמכים (רלוונטיים ל-gpt-image-2)

| פרמטר | ערכים | ברירת מחדל |
|-------|-------|------------|
| `model` | `gpt-image-2` | — (חובה) |
| `prompt` | טקסט (עד ~32,000 תווים) | — (חובה) |
| `size` | `1024x1024`, `1536x1024`, `1024x1536`, `2048x2048`, `3840x2160`, `auto`, או `WIDTHxHEIGHT` מותאם אישית | `auto` |
| `quality` | `low`, `medium`, `high`, `auto` | `auto` |
| `output_format` | `png`, `jpeg`, `webp` | `png` |
| `n` | מספר תמונות (1-10) | 1 |
| `background` | `transparent`, `opaque`, `auto` | `auto` (שימו לב: `transparent` לא נתמך במפורש עבור gpt-image-2 בחלק מהתצורות) |

## טיפול בשגיאות

- **תגובת JSON ללא שדה `data`** → כמעט תמיד שגיאת API (מפתח לא תקין, לא עבר Organization Verification, פרמטר לא חוקי). הדפיסי את תוכן התגובה המלא כדי לאבחן — אל תניחי שהבעיה במודל.
- **קובץ תמונה בגודל 0 בייטים** → סימן ש-`b64_json` היה ריק/null (למשל אם התגובה הייתה שגיאה ולא תמונה). בדקי את קובץ ה-JSON הגולמי של התגובה לפני שמדווחים על הצלחה.
