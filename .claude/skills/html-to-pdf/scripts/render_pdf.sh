#!/bin/bash
# מרנדר קובץ HTML מקומי ל-PDF ויזואלי, דרך Chrome headless (מותקן כבר במחשב -
# אין תלות חדשה). נועד בעיקר לתת "תצוגה מקדימה" שנפתחת ויזואלית ב-Google Drive
# (בניגוד לקובץ ה-HTML עצמו, ש-Drive תמיד מציג כקוד גולמי, לא מרונדר).
#
# שימוש:
#   render_pdf.sh <input.html> [output.pdf]
# אם output.pdf לא סופק, נשמר לצד קובץ הקלט עם אותו שם ו-.pdf.

set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -x "$CHROME" ]; then
  echo '{"error": "Google Chrome לא נמצא ב-/Applications - נדרש להתקנה"}' >&2
  exit 1
fi

INPUT="$1"
if [ ! -f "$INPUT" ]; then
  echo "{\"error\": \"הקובץ לא נמצא: $INPUT\"}" >&2
  exit 1
fi

OUTPUT="${2:-${INPUT%.*}.pdf}"
ABS_INPUT="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"

"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUTPUT" "file://$ABS_INPUT" >/dev/null 2>&1

if [ ! -s "$OUTPUT" ]; then
  echo "{\"error\": \"רינדור ה-PDF נכשל, הקובץ לא נוצר: $OUTPUT\"}" >&2
  exit 1
fi

echo "{\"pdf\": \"$OUTPUT\"}"
