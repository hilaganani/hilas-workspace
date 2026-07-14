#!/usr/bin/env python3
"""
בודק קריאות בעברית לפי יעדי Yoast: אחוז משפטים מעל 15 מילה, ואחוז משפטים בקול פסיבי.
מחליף את ההערכה הידנית שדני עשה בעבר (ראו .claude/agents/dani.md).

שימוש:
    python3 readability_he.py <path-to-markdown-file>

פלט: JSON ל-stdout.

הערה על מהימנות: זיהוי הקול הפעיל/פסיבי בעברית ללא ניקוד הוא הערכה היוריסטית
(רשימת צורות פועל נפוצות בבניין נפעל/פועל/הופעל + הביטוי "על ידי"), לא ניתוח
דקדוקי מלא. זה עדיף על הערכה ידנית (עקבי, ניתן לשחזור), אבל עדיין לא מדויק
ב-100% — ייתכנו false positive/negative בודדים. יש לקרוא את רשימת המשפטים
המסומנים ("passive_sentences") ולא רק את האחוז, כדי לוודא שהתוצאה הגיונית.
"""

import json
import re
import sys

# צורות פסיביות נפוצות בתוכן שיווקי/בלוג בעברית (בניין נפעל/פועל/הופעל).
# זו רשימה סגורה, לא regex גורף על "מילים שמתחילות בנ'" — כי זה היה תופס
# גם שמות תואר כמו "נחמד"/"נכון"/"נמוך" שאינם פעלים בכלל.
PASSIVE_WORDS = {
    "נעשה", "נעשית", "נעשתה", "נעשו",
    "נכתב", "נכתבה", "נכתבו", "נכתבים", "נכתבות",
    "נבנה", "נבנתה", "נבנו",
    "נמצא", "נמצאה", "נמצאו",
    "נבדק", "נבדקה", "נבדקו",
    "נבחר", "נבחרה", "נבחרו",
    "נערך", "נערכה", "נערכו",
    "נוצר", "נוצרה", "נוצרו",
    "נשלח", "נשלחה", "נשלחו",
    "נסגר", "נסגרה", "נסגרו",
    "נפתח", "נפתחה", "נפתחו",
    "נמכר", "נמכרה", "נמכרו",
    "נקבע", "נקבעה", "נקבעו",
    "נאסף", "נאספה", "נאספו",
    "נלמד", "נלמדה", "נלמדו",
    "נדרש", "נדרשת", "נדרשו",
    "בוצע", "בוצעה", "בוצעו",
    "מבוצע", "מבוצעת", "מבוצעים", "מבוצעות",
    "מתבצע", "מתבצעת", "מתבצעים", "מתבצעות",
    "יבוצע", "תבוצע", "יבוצעו",
    "הופעל", "הופעלה", "הופעלו",
    "מופעל", "מופעלת", "מופעלים", "מופעלות",
    "הוצג", "הוצגה", "הוצגו",
    "מוצג", "מוצגת", "מוצגים", "מוצגות",
    "הוגש", "הוגשה", "הוגשו",
    "מוגש", "מוגשת",
}

AGENT_PHRASE = "על ידי"  # ביטוי הסוכן הפסיבי החד-משמעי ביותר בעברית ("by" באנגלית)

WORD_THRESHOLD = 15  # יעד Yoast: משפט "ארוך" הוא מעל 15 מילה
MAX_LONG_SENTENCE_PCT = 25  # יעד Yoast: לכל היותר 25% מהמשפטים ארוכים
MAX_PASSIVE_PCT = 10  # יעד Yoast: לכל היותר 10% מהמשפטים בקול פסיבי


def strip_markdown(text: str) -> str:
    """מסיר כותרות, בולטים, קוד, טבלאות, לינקים ו-placeholders — משאיר רק פרוזה."""
    lines = []
    in_code_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if re.match(r"^[-*+]\s", stripped) or re.match(r"^\d+\.\s", stripped):
            continue  # שורת רשימה/בולט — לא נכללת בניתוח קריאות (כמו ב-Yoast)
        if stripped.startswith(">"):
            stripped = stripped.lstrip("> ").strip()
        if "|" in stripped and stripped.count("|") >= 2:
            continue  # שורת טבלה — לא פרוזה רגילה
        stripped = re.sub(r"\{\{IMAGE_NEEDED:.*?\}\}", "", stripped)
        stripped = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)  # [text](url) -> text
        stripped = re.sub(r"[*_`]", "", stripped)
        if stripped:
            lines.append(stripped)
    return " ".join(lines)


def split_sentences(text: str) -> list:
    """מפצל לפי סימני סיום משפט (. ! ?), עם רווח/סוף שורה אחריהם."""
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if s.strip()]


def count_words(sentence: str) -> int:
    words = re.findall(r"[א-ת\w'\"-]+", sentence)
    return len(words)


def is_passive(sentence: str) -> bool:
    if AGENT_PHRASE in sentence:
        return True
    words = re.findall(r"[א-ת]+", sentence)
    return any(w in PASSIVE_WORDS for w in words)


def analyze(text: str) -> dict:
    prose = strip_markdown(text)
    sentences = split_sentences(prose)
    total = len(sentences)
    if total == 0:
        return {
            "total_sentences": 0,
            "long_sentence_pct": 0,
            "passive_pct": 0,
            "meets_length_target": True,
            "meets_passive_target": True,
            "long_sentences": [],
            "passive_sentences": [],
            "note": "לא נמצאו משפטי פרוזה לניתוח (רק כותרות/רשימות/טבלאות/קוד).",
        }

    long_sentences = [s for s in sentences if count_words(s) > WORD_THRESHOLD]
    passive_sentences = [s for s in sentences if is_passive(s)]

    long_pct = round(len(long_sentences) / total * 100, 1)
    passive_pct = round(len(passive_sentences) / total * 100, 1)

    return {
        "total_sentences": total,
        "long_sentence_pct": long_pct,
        "passive_pct": passive_pct,
        "meets_length_target": long_pct <= MAX_LONG_SENTENCE_PCT,
        "meets_passive_target": passive_pct <= MAX_PASSIVE_PCT,
        "long_sentences": long_sentences,
        "passive_sentences": passive_sentences,
        "note": "זיהוי קול פסיבי הוא היוריסטי (רשימת צורות + 'על ידי') — יש לעבור על passive_sentences ולוודא שהתוצאה הגיונית, לא להסתמך על האחוז בלבד.",
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "שימוש: python3 readability_he.py <path-to-markdown-file>"}, ensure_ascii=False))
        sys.exit(1)
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(json.dumps({"error": f"הקובץ לא נמצא: {path}"}, ensure_ascii=False))
        sys.exit(1)

    result = analyze(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
