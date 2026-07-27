#!/usr/bin/env python3
"""
משבץ את חבילת ה-SEO של דני (קובץ .md מ-dani/outputs/) בתחתית קובץ ה-HTML של
המאמר עצמו, כבלוק מופרד ומסומן בבירור - כדי שהילה לא תצטרך לחפש את ההוראות
בקובץ נפרד בזמן הפרסום.

הבלוק נוסף אחרי </main> ולפני </body>, עטוף בהערות HTML מפורשות
(SEO-PACKAGE-START / SEO-PACKAGE-END) כדי שיהיה קל להסיר אותו, וכדי שהרצה
חוזרת תחליף את הבלוק הקיים במקום לשכפל אותו.

שימוש:
    python3 embed_seo.py --html output/article.html --seo dani/outputs/article-seo.md

אין תלויות חיצוניות - ממיר Markdown מינימלי מובנה (כותרות, טבלאות, רשימות,
הדגשות, ציטוטים, קוד inline). מכוון בדיוק לפורמט שדני מייצר, לא ממיר Markdown כללי.
"""

import argparse
import html as html_mod
import os
import re
import sys

START_MARKER = "<!-- SEO-PACKAGE-START (לא לפרסום - הוראות פנימיות) -->"
END_MARKER = "<!-- SEO-PACKAGE-END -->"

# הכותרת של סעיף חבילת הפרסום בקובץ ה-seo.md של דני. הניסוח השתנה בין ריצות
# היסטוריות ("חבילת SEO סופית" / "חבילת מטא-דאטה" / "חבילת SEO לפרסום"), ולכן
# מזוהות כמה וריאציות. הפורמט המחייב מכאן ואילך מתועד ב-.claude/agents/dani.md.
PACKAGE_HEADING = re.compile(
    r"^(#{2,4})\s*(?:\d+[.)]\s*)?.*?"
    r"(?:חבילת\s+SEO\s+סופית|חבילת\s+SEO\s+לפרסום|חבילת\s+מטא[-\s]?דאטה)",
    re.MULTILINE,
)

BLOCK_CSS = """
<style>
.seo-package {
  max-width: 760px;
  margin: 64px auto 0;
  padding: 0 24px 64px;
  font-family: "Assistant", "Heebo", "Segoe UI", Tahoma, Arial, sans-serif;
  direction: rtl;
  text-align: right;
  color: #2E2150;
  line-height: 1.8;
}
.seo-package .seo-divider {
  border: 0;
  border-top: 2px dashed #B79BE1;
  margin: 0 0 28px;
}
.seo-package .seo-banner {
  background: #F7F3FD;
  border: 1px solid #D2BBF2;
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 24px;
  font-size: 0.95rem;
  color: #49318E;
  font-weight: 700;
}
.seo-package h2 {
  font-family: "Heebo", "Segoe UI", Tahoma, Arial, sans-serif;
  font-size: 1.35rem;
  color: #49318E;
  margin: 1.6em 0 0.5em;
  border: 0;
  padding: 0;
}
.seo-package h3 {
  font-family: "Heebo", "Segoe UI", Tahoma, Arial, sans-serif;
  font-size: 1.1rem;
  color: #2E2150;
  margin: 1.4em 0 0.4em;
  border-right: 4px solid #8762B5;
  padding-right: 0.6em;
}
.seo-package p { margin: 0.7em 0; font-size: 1rem; }
.seo-package ul, .seo-package ol { margin: 0.6em 0; padding-right: 1.4em; padding-left: 0; }
.seo-package li { margin-bottom: 0.35em; }
.seo-package blockquote {
  margin: 0.6em 0;
  padding: 10px 16px;
  background: #fff;
  border-right: 4px solid #49318E;
  border-radius: 8px;
  font-weight: 700;
}
.seo-package code {
  background: #EFE8FA;
  padding: 1px 6px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.92em;
  direction: ltr;
  display: inline-block;
}
.seo-package table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  background: #fff;
  font-size: 0.95rem;
}
.seo-package th, .seo-package td {
  border: 1px solid #E4DAF3;
  padding: 8px 12px;
  text-align: right;
  vertical-align: top;
}
.seo-package th { background: #F7F3FD; color: #49318E; }
.seo-package hr { border: 0; border-top: 1px solid #E4DAF3; margin: 1.6em 0; }
</style>
"""

BANNER = (
    '<div class="seo-banner">חבילת ה-SEO של דני - לשימוש פנימי בזמן הפרסום בלבד. '
    'אין להעתיק את החלק הזה לגוף המאמר באתר.</div>'
)


def esc(text):
    return html_mod.escape(text, quote=False)


def inline(text):
    """המרות inline: קוד, מודגש, נטוי, קישורים. הסדר חשוב - קוד קודם, כדי שלא נפרש
    תווי Markdown בתוך מקטע קוד."""
    placeholders = []

    def stash_code(m):
        placeholders.append(f"<code>{esc(m.group(1))}</code>")
        return f"\x00{len(placeholders) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = esc(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: placeholders[int(m.group(1))], text)


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def md_to_html(md):
    lines = md.split("\n")
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            out.append("<hr>")
            i += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            # דני משתמש ב-## לכותרת החבילה ו-### לסעיפים; ממפים לרמה אחת פנימה
            # כדי לא להתנגש בהיררכיית הכותרות של המאמר עצמו.
            level = min(len(heading.group(1)) + 1, 6)
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        # טבלה: שורת כותרת + שורת מפריד
        if stripped.startswith("|") and i + 1 < n and re.fullmatch(
            r"\|[\s:|-]+\|", lines[i + 1].strip()
        ):
            headers = split_row(stripped)
            out.append("<table><thead><tr>")
            out.extend(f"<th>{inline(h)}</th>" for h in headers)
            out.append("</tr></thead><tbody>")
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                out.append("<tr>")
                out.extend(f"<td>{inline(c)}</td>" for c in split_row(lines[i]))
                out.append("</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        if stripped.startswith(">"):
            block = []
            while i < n and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(block))}</blockquote>")
            continue

        if re.match(r"^[-*+]\s+", stripped):
            out.append("<ul>")
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                item = re.sub(r"^[-*+]\s+", "", lines[i].strip())
                out.append("<li>" + inline(item) + "</li>")
                i += 1
            out.append("</ul>")
            continue

        if re.match(r"^\d+[.)]\s+", stripped):
            out.append("<ol>")
            while i < n and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                item = re.sub(r"^\d+[.)]\s+", "", lines[i].strip())
                out.append("<li>" + inline(item) + "</li>")
                i += 1
            out.append("</ol>")
            continue

        para = []
        while i < n and lines[i].strip() and not re.match(
            r"^(#{1,6}\s|>|\||[-*+]\s|\d+[.)]\s)", lines[i].strip()
        ) and not re.fullmatch(r"-{3,}|\*{3,}|_{3,}", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")

    return "\n".join(out)


def extract_package(md):
    """מחזיר רק את סעיף 'חבילת ה-SEO הסופית לפרסום' מתוך קובץ ה-seo.md המלא.

    שאר הקובץ (אימות קישורים פנימיים, מספרי קריאות, הערות שיפור) הוא תיעוד
    QA של תהליך העבודה - לא הוראות פרסום - ולכן לא משובץ ב-HTML של המאמר.
    """
    matches = list(PACKAGE_HEADING.finditer(md))
    if not matches:
        return None

    # כותרת המסמך עצמו (בראש הקובץ) נקראת לעיתים "חבילת SEO לפרסום: <שם המאמר>",
    # ולכן מתאימה לתבנית אבל אינה הסעיף המבוקש - מעדיפים תמיד התאמה פנימית.
    inner = [m for m in matches if m.start() > 0]
    if inner:
        match = inner[0]
    else:
        match = matches[0]
        print(
            "אזהרה: ההתאמה היחידה היא כותרת המסמך עצמו - משובץ הקובץ במלואו.",
            file=sys.stderr,
        )

    level = len(match.group(1))
    start = match.start()
    # הסעיף נמשך עד הכותרת הבאה באותה רמה או גבוהה ממנה
    next_heading = re.compile(r"^#{1," + str(level) + r"}\s", re.MULTILINE)
    following = next_heading.search(md, match.end())
    return md[start:following.start()].strip() if following else md[start:].strip()


def main():
    parser = argparse.ArgumentParser(
        description="Embed Dani's SEO package into the bottom of an article HTML file"
    )
    parser.add_argument("--html", required=True, help="path to the article .html file")
    parser.add_argument("--seo", required=True, help="path to Dani's -seo.md file")
    args = parser.parse_args()

    for path in (args.html, args.seo):
        if not os.path.isfile(path):
            print(f"שגיאה: הקובץ לא נמצא: {path}", file=sys.stderr)
            sys.exit(1)

    with open(args.html, "r", encoding="utf-8") as f:
        doc = f.read()
    with open(args.seo, "r", encoding="utf-8") as f:
        seo_md = f.read()

    package = extract_package(seo_md)
    if package is None:
        print(
            f"שגיאה: לא נמצא סעיף 'חבילת SEO סופית/מטא-דאטה' ב-{args.seo}. "
            "ודאו שדני שמר את החבילה תחת כותרת בפורמט המחייב "
            "(ראו .claude/agents/dani.md). לא שובץ דבר.",
            file=sys.stderr,
        )
        sys.exit(1)
    seo_md = package

    block = "\n".join([
        START_MARKER,
        BLOCK_CSS.strip(),
        '<section class="seo-package">',
        '<hr class="seo-divider">',
        BANNER,
        md_to_html(seo_md),
        "</section>",
        END_MARKER,
        "",
    ])

    # הרצה חוזרת מחליפה בלוק קיים, לא משכפלת אותו
    existing = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER) + r"\n?",
        re.DOTALL,
    )
    if existing.search(doc):
        doc = existing.sub(block, doc)
        action = "replaced"
    elif "</body>" in doc:
        doc = doc.replace("</body>", block + "</body>", 1)
        action = "inserted"
    else:
        doc = doc.rstrip() + "\n" + block
        action = "appended"

    with open(args.html, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f'{{"html": "{args.html}", "seo": "{args.seo}", "action": "{action}"}}')


if __name__ == "__main__":
    main()
