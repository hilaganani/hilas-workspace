# Content Feedback Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing, mostly-idle "תכנון תוכן חודשי" Airtable table into the single source of truth for plan-vs-actual content tracking, closing the loop between Yael's monthly plans and what Hila actually publishes/changes/skips — with minimal manual effort from Hila (one biweekly digest reply) and no new persona added to the team.

**Architecture:** A new narrow Airtable skill (`airtable-content-calendar`) provides exactly two operations — create rows (status always `מתוכנן`) and update three fields only (`סטטוס`/`הערה`/`קישור/גרסה סופית`) by the table's own Autonumber field. Yael seeds rows when she finalizes a monthly plan and reads the history back in for insights when planning the next one; she never runs the update operation herself. A biweekly scheduled job asks Roi to draft a neutral-toned digest of pending items and sends it via the existing `email-send` skill; when Hila replies in chat, Roi maps her reply to Autonumber values and dispatches the generic catch-all agent (not a roster persona) to run the restricted update.

**Tech Stack:** Python 3 + `requests` (already used by `smoove-newsletter`/`google-search-console` skills in this repo), Airtable REST API. No test framework is installed in this repo (no pytest) — tests use the Python stdlib `unittest` module, run via `python3 -m unittest`.

**Full design reference:** [`docs/superpowers/specs/2026-07-15-content-feedback-loop-design.md`](../specs/2026-07-15-content-feedback-loop-design.md) — read it once before starting; this plan implements it task-by-task and does not repeat its rationale.

## Global Constraints

- Table ID for "תכנון תוכן חודשי" is `tbl6S09qb9wK2ARW6` — hardcoded, per this project's existing convention (`airtable-write`'s `tbl1eG92lW0vsY0tc` is hardcoded the same way).
- Env vars: `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID` (same as `airtable-read`/`airtable-write`; already present in this repo's `.env`).
- The update operation may **only ever** touch the fields `סטטוס`, `הערה`, `קישור/גרסה סופית` — never `שבוע / תאריך יעד`, `ערוץ`, `נושא`, or any other field. This is enforced in code (`build_update_fields`), not just documented.
- Never pass `typecast` to any Airtable write call, per this project's established safety rule (see `airtable-write/SKILL.md`).
- Instagram Stories are never rows in this table — out of scope by design (see spec §3).
- No pytest, no new Python dependency beyond `requests` (already required elsewhere in this repo).
- Tasks 10 and 11 have real-world side effects (writing to Hila's live Airtable base; creating a recurring automated email). Do not run them without pausing to confirm with the user first, even though the plan documents the exact steps.

---

### Task 1: `content_calendar.py` core logic (constants, chunking, field builders)

**Files:**
- Create: `.claude/skills/airtable-content-calendar/scripts/content_calendar.py`
- Create: `.claude/skills/airtable-content-calendar/scripts/test_content_calendar.py`

**Interfaces:**
- Produces: `ALLOWED_CHANNELS: set[str]`, `ALLOWED_STATUSES: set[str]`, `DEFAULT_STATUS: str`, `TABLE_ID: str`, `chunked(seq: list, size: int) -> Iterator[list]`, `build_create_fields(item: dict) -> dict`, `build_update_fields(update: dict) -> dict`. Later tasks (2, 3) import and call these.

- [ ] **Step 1: Create the skill directory and write the failing test**

```bash
mkdir -p "/Users/hilaganani/Documents/workspace/hilas-workspace/.claude/skills/airtable-content-calendar/scripts"
```

Create `.claude/skills/airtable-content-calendar/scripts/test_content_calendar.py`:

```python
import unittest

from content_calendar import (
    ALLOWED_CHANNELS,
    ALLOWED_STATUSES,
    DEFAULT_STATUS,
    build_create_fields,
    build_update_fields,
    chunked,
)


class TestChunked(unittest.TestCase):
    def test_splits_into_full_and_partial_batches(self):
        items = list(range(12))
        batches = list(chunked(items, 10))
        self.assertEqual(batches, [list(range(10)), [10, 11]])

    def test_empty_input_yields_no_batches(self):
        self.assertEqual(list(chunked([], 10)), [])


class TestBuildCreateFields(unittest.TestCase):
    def test_valid_item_gets_default_status(self):
        item = {"week_or_date": "2026-07-14", "channel": "בלוג", "topic": "5 סימנים..."}
        fields = build_create_fields(item)
        self.assertEqual(
            fields,
            {
                "שבוע / תאריך יעד": "2026-07-14",
                "ערוץ": "בלוג",
                "נושא": "5 סימנים...",
                "סטטוס": DEFAULT_STATUS,
            },
        )

    def test_unknown_channel_raises(self):
        item = {"week_or_date": "2026-07-14", "channel": "וואטסאפ", "topic": "x"}
        with self.assertRaises(ValueError):
            build_create_fields(item)

    def test_all_allowed_channels_are_accepted(self):
        for channel in ALLOWED_CHANNELS:
            item = {"week_or_date": "2026-07-14", "channel": channel, "topic": "x"}
            fields = build_create_fields(item)
            self.assertEqual(fields["ערוץ"], channel)


class TestBuildUpdateFields(unittest.TestCase):
    def test_status_only(self):
        update = {"serial": 1, "status": "פורסם"}
        self.assertEqual(build_update_fields(update), {"סטטוס": "פורסם"})

    def test_status_with_note_and_final_link(self):
        update = {
            "serial": 2,
            "status": "שונה",
            "note": "עשיתי גרסה אחרת לטיקטוק",
            "final_link": "https://example.com/final",
        }
        self.assertEqual(
            build_update_fields(update),
            {
                "סטטוס": "שונה",
                "הערה": "עשיתי גרסה אחרת לטיקטוק",
                "קישור/גרסה סופית": "https://example.com/final",
            },
        )

    def test_empty_note_is_omitted(self):
        update = {"serial": 3, "status": "לא עלה", "note": ""}
        self.assertEqual(build_update_fields(update), {"סטטוס": "לא עלה"})

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            build_update_fields({"serial": 4, "status": "בתהליך"})

    def test_all_allowed_statuses_are_accepted(self):
        for status in ALLOWED_STATUSES:
            fields = build_update_fields({"serial": 1, "status": status})
            self.assertEqual(fields["סטטוס"], status)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace/.claude/skills/airtable-content-calendar/scripts" && python3 -m unittest test_content_calendar -v
```

Expected: `ModuleNotFoundError: No module named 'content_calendar'` (the module doesn't exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `.claude/skills/airtable-content-calendar/scripts/content_calendar.py`:

```python
#!/usr/bin/env python3
"""
יוצר ומעדכן רשומות בטבלת "תכנון תוכן חודשי" ב-Airtable (tbl6S09qb9wK2ARW6) -
מקור האמת ליומן תכנון-מול-ביצוע (ראו CLAUDE.md, סעיף "Feedback loop: plan vs. actual").

שתי פעולות בלבד, לפי עקרון הרשאות מינימליות:
    create-items  - יצירת שורות חדשות (סטטוס תמיד "מתוכנן")
    update-items  - עדכון סטטוס/הערה/קישור-גרסה-סופית בלבד, לפי "מספר סידורי"
                    (לעולם לא שדות אסטרטגיה: שבוע/ערוץ/נושא, לעולם לא מחיקה,
                    לעולם לא טבלה אחרת)

שימוש:
    python3 content_calendar.py create-items --items-json items.json
    python3 content_calendar.py update-items --updates-json updates.json

דורש ב-.env:
    AIRTABLE_API_KEY, AIRTABLE_BASE_ID (אותם משתנים כמו airtable-read/airtable-write)

דורש: pip3 install requests
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print(json.dumps({"error": "חסרה חבילת requests. הריצו: pip3 install requests"}, ensure_ascii=False))
    sys.exit(1)

TABLE_ID = "tbl6S09qb9wK2ARW6"  # תכנון תוכן חודשי
API_BASE = "https://api.airtable.com/v0"

ALLOWED_CHANNELS = {"בלוג", "ניוזלטר", "לינקדאין", "פייסבוק/אינסטגרם", "טיקטוק"}
ALLOWED_STATUSES = {"פורסם", "שונה", "לא עלה"}
DEFAULT_STATUS = "מתוכנן"
BATCH_SIZE = 10  # מגבלת Airtable ליצירה/עדכון מרובה-רשומות בקריאה אחת


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def build_create_fields(item):
    channel = item["channel"]
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"ערוץ לא מוכר: {channel!r} (מותר: {sorted(ALLOWED_CHANNELS)})")
    return {
        "שבוע / תאריך יעד": item["week_or_date"],
        "ערוץ": channel,
        "נושא": item["topic"],
        "סטטוס": DEFAULT_STATUS,
    }


def build_update_fields(update):
    status = update["status"]
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"סטטוס לא מוכר: {status!r} (מותר: {sorted(ALLOWED_STATUSES)})")
    fields = {"סטטוס": status}
    if update.get("note"):
        fields["הערה"] = update["note"]
    if update.get("final_link"):
        fields["קישור/גרסה סופית"] = update["final_link"]
    return fields


if __name__ == "__main__":
    print(json.dumps({"error": "CLI not implemented yet — see Task 2/3"}, ensure_ascii=False))
    sys.exit(1)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace/.claude/skills/airtable-content-calendar/scripts" && python3 -m unittest test_content_calendar -v
```

Expected: `OK` — all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
git add .claude/skills/airtable-content-calendar/scripts/content_calendar.py .claude/skills/airtable-content-calendar/scripts/test_content_calendar.py
git commit -m "Add core field-builder logic for airtable-content-calendar skill"
```

---

### Task 2: `create-items` CLI command

**Files:**
- Modify: `.claude/skills/airtable-content-calendar/scripts/content_calendar.py`
- Modify: `.claude/skills/airtable-content-calendar/scripts/test_content_calendar.py`

**Interfaces:**
- Consumes: `chunked`, `build_create_fields`, `TABLE_ID`, `API_BASE`, `BATCH_SIZE` from Task 1.
- Produces: `get_env() -> (api_key, base_id)`, `get_headers(api_key) -> dict`, `cmd_create_items(args)` — later tasks (3) reuse `get_env`/`get_headers`; the `SKILL.md` in Task 4 documents this exact CLI invocation.

- [ ] **Step 1: Write the failing test**

Append to `.claude/skills/airtable-content-calendar/scripts/test_content_calendar.py` (add these imports to the top `from content_calendar import (...)` line: `cmd_create_items`, and add `import io, json as json_module, sys` — actually just add `from unittest import mock` and `import io, json, tempfile, os, contextlib` at the top of the file):

```python
import contextlib
import io
import json
import os
import tempfile
from unittest import mock

from content_calendar import cmd_create_items  # add to the existing import line instead if preferred
```

Add this test class at the end of the file (before `if __name__ == "__main__":`):

```python
class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestCmdCreateItems(unittest.TestCase):
    def _write_items(self, items):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(items, f)
        f.close()
        return f.name

    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    @mock.patch("content_calendar.requests.post")
    def test_creates_records_in_single_batch(self, mock_post):
        items = [
            {"week_or_date": "2026-07-14", "channel": "בלוג", "topic": "מאמר A"},
            {"week_or_date": "2026-07-14", "channel": "טיקטוק", "topic": "וידאו B"},
        ]
        path = self._write_items(items)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "records": [{"id": "rec1"}, {"id": "rec2"}]
        }

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_create_items(Args(items_json=path))

        os.unlink(path)
        self.assertEqual(mock_post.call_count, 1)
        _, kwargs = mock_post.call_args
        self.assertEqual(len(kwargs["json"]["records"]), 2)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["created"], 2)

    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    @mock.patch("content_calendar.requests.post")
    def test_batches_in_groups_of_ten(self, mock_post):
        items = [
            {"week_or_date": "2026-07-14", "channel": "בלוג", "topic": f"מאמר {i}"}
            for i in range(12)
        ]
        path = self._write_items(items)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.side_effect = [
            {"records": [{"id": f"rec{i}"} for i in range(10)]},
            {"records": [{"id": "rec10"}, {"id": "rec11"}]},
        ]

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_create_items(Args(items_json=path))

        os.unlink(path)
        self.assertEqual(mock_post.call_count, 2)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["created"], 12)

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_missing_env_exits_nonzero(self):
        items = [{"week_or_date": "2026-07-14", "channel": "בלוג", "topic": "x"}]
        path = self._write_items(items)
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(buf):
                cmd_create_items(Args(items_json=path))
        os.unlink(path)
        self.assertNotEqual(ctx.exception.code, 0)

    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    def test_unknown_channel_exits_nonzero_without_calling_api(self):
        items = [{"week_or_date": "2026-07-14", "channel": "וואטסאפ", "topic": "x"}]
        path = self._write_items(items)
        buf = io.StringIO()
        with mock.patch("content_calendar.requests.post") as mock_post:
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stdout(buf):
                    cmd_create_items(Args(items_json=path))
            mock_post.assert_not_called()
        os.unlink(path)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace/.claude/skills/airtable-content-calendar/scripts" && python3 -m unittest test_content_calendar -v
```

Expected: `ImportError: cannot import name 'cmd_create_items'`.

- [ ] **Step 3: Implement `get_env`, `get_headers`, `cmd_create_items`, and the `create-items` CLI subcommand**

In `content_calendar.py`, replace the final block:

```python
if __name__ == "__main__":
    print(json.dumps({"error": "CLI not implemented yet — see Task 2/3"}, ensure_ascii=False))
    sys.exit(1)
```

with:

```python
def get_env():
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = os.environ.get("AIRTABLE_BASE_ID")
    if not api_key or not base_id:
        print(json.dumps({"error": "AIRTABLE_API_KEY ו/או AIRTABLE_BASE_ID לא מוגדרים ב-.env"}, ensure_ascii=False))
        sys.exit(1)
    return api_key, base_id


def get_headers(api_key):
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def cmd_create_items(args):
    api_key, base_id = get_env()
    with open(args.items_json, encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print(json.dumps({"error": "רשימת הפריטים ריקה"}, ensure_ascii=False))
        sys.exit(1)

    try:
        records = [{"fields": build_create_fields(item)} for item in items]
    except (KeyError, ValueError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

    created = []
    for batch in chunked(records, BATCH_SIZE):
        resp = requests.post(
            f"{API_BASE}/{base_id}/{TABLE_ID}",
            headers=get_headers(api_key),
            json={"records": batch},
            timeout=30,
        )
        if resp.status_code >= 400:
            print(json.dumps(
                {"error": "יצירת פריטים נכשלה", "status": resp.status_code, "body": resp.text, "created_so_far": len(created)},
                ensure_ascii=False, indent=2,
            ))
            sys.exit(1)
        created.extend(resp.json().get("records", []))

    print(json.dumps({"created": len(created), "records": created}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Airtable content-calendar create+restricted-update (תכנון תוכן חודשי)")
    sub = parser.add_subparsers(dest="action", required=True)

    p_create = sub.add_parser("create-items", help="create new planned rows (status always מתוכנן)")
    p_create.add_argument("--items-json", required=True, help="JSON file: array of {week_or_date, channel, topic}")
    p_create.set_defaults(func=cmd_create_items)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace/.claude/skills/airtable-content-calendar/scripts" && python3 -m unittest test_content_calendar -v
```

Expected: `OK` — all tests pass (9 from Task 1 + 4 new = 13).

- [ ] **Step 5: Commit**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
git add .claude/skills/airtable-content-calendar/scripts/content_calendar.py .claude/skills/airtable-content-calendar/scripts/test_content_calendar.py
git commit -m "Add create-items CLI command to airtable-content-calendar"
```

---

### Task 3: `update-items` CLI command (lookup by מספר סידורי + restricted PATCH)

**Files:**
- Modify: `.claude/skills/airtable-content-calendar/scripts/content_calendar.py`
- Modify: `.claude/skills/airtable-content-calendar/scripts/test_content_calendar.py`

**Interfaces:**
- Consumes: `get_env`, `get_headers`, `build_update_fields`, `TABLE_ID`, `API_BASE` from Tasks 1-2.
- Produces: `find_record_by_serial(api_key, base_id, serial) -> str | None`, `cmd_update_items(args)`. The `SKILL.md` in Task 4 documents this CLI invocation; `roi.md` (Task 8) references it by exact command.

- [ ] **Step 1: Write the failing test**

Add `cmd_update_items` and `find_record_by_serial` to the import line at the top of `test_content_calendar.py`, and append this test class before `if __name__ == "__main__":`:

```python
class TestFindRecordBySerial(unittest.TestCase):
    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    @mock.patch("content_calendar.requests.get")
    def test_returns_record_id_when_found(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"records": [{"id": "recABC"}]}

        result = find_record_by_serial("key123", "appXYZ", 5)

        self.assertEqual(result, "recABC")
        _, kwargs = mock_get.call_args
        self.assertIn("מספר סידורי", kwargs["params"]["filterByFormula"])
        self.assertIn("5", kwargs["params"]["filterByFormula"])

    @mock.patch("content_calendar.requests.get")
    def test_returns_none_when_not_found(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"records": []}

        result = find_record_by_serial("key123", "appXYZ", 999)

        self.assertIsNone(result)

    @mock.patch("content_calendar.requests.get")
    def test_raises_on_api_error(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "server error"

        with self.assertRaises(RuntimeError):
            find_record_by_serial("key123", "appXYZ", 1)


class TestCmdUpdateItems(unittest.TestCase):
    def _write_updates(self, updates):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(updates, f)
        f.close()
        return f.name

    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    @mock.patch("content_calendar.requests.patch")
    @mock.patch("content_calendar.find_record_by_serial")
    def test_updates_multiple_items(self, mock_find, mock_patch):
        updates = [
            {"serial": 1, "status": "פורסם"},
            {"serial": 2, "status": "שונה", "note": "גרסה אחרת לטיקטוק"},
        ]
        path = self._write_updates(updates)
        mock_find.side_effect = ["rec1", "rec2"]
        mock_patch.return_value.status_code = 200

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_update_items(Args(updates_json=path))

        os.unlink(path)
        self.assertEqual(mock_patch.call_count, 2)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["succeeded"], 2)
        self.assertEqual(output["failed"], 0)

    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    @mock.patch("content_calendar.find_record_by_serial")
    def test_serial_not_found_is_reported_not_fatal_for_other_items(self, mock_find):
        updates = [{"serial": 999, "status": "פורסם"}]
        path = self._write_updates(updates)
        mock_find.return_value = None

        buf = io.StringIO()
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stdout(buf):
                cmd_update_items(Args(updates_json=path))

        os.unlink(path)
        output = json.loads(buf.getvalue())
        self.assertEqual(output["failed"], 1)
        self.assertIn("לא נמצאה רשומה", output["results"][0]["error"])

    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    def test_invalid_status_never_calls_patch(self):
        updates = [{"serial": 1, "status": "בתהליך"}]
        path = self._write_updates(updates)

        with mock.patch("content_calendar.requests.patch") as mock_patch:
            buf = io.StringIO()
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stdout(buf):
                    cmd_update_items(Args(updates_json=path))
            mock_patch.assert_not_called()

        os.unlink(path)

    @mock.patch.dict(os.environ, {"AIRTABLE_API_KEY": "key123", "AIRTABLE_BASE_ID": "appXYZ"})
    @mock.patch("content_calendar.requests.patch")
    @mock.patch("content_calendar.find_record_by_serial")
    def test_patch_payload_never_contains_strategy_fields(self, mock_find, mock_patch):
        updates = [{"serial": 1, "status": "פורסם", "note": "הערה", "final_link": "https://x"}]
        path = self._write_updates(updates)
        mock_find.return_value = "rec1"
        mock_patch.return_value.status_code = 200

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_update_items(Args(updates_json=path))

        os.unlink(path)
        _, kwargs = mock_patch.call_args
        sent_fields = set(kwargs["json"]["fields"].keys())
        self.assertEqual(sent_fields, {"סטטוס", "הערה", "קישור/גרסה סופית"})
        self.assertNotIn("ערוץ", sent_fields)
        self.assertNotIn("נושא", sent_fields)
        self.assertNotIn("שבוע / תאריך יעד", sent_fields)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace/.claude/skills/airtable-content-calendar/scripts" && python3 -m unittest test_content_calendar -v
```

Expected: `ImportError: cannot import name 'find_record_by_serial'`.

- [ ] **Step 3: Implement `find_record_by_serial`, `cmd_update_items`, and register the `update-items` subcommand**

In `content_calendar.py`, insert before `def main():`:

```python
def find_record_by_serial(api_key, base_id, serial):
    formula = f"{{מספר סידורי}} = {int(serial)}"
    resp = requests.get(
        f"{API_BASE}/{base_id}/{TABLE_ID}",
        headers=get_headers(api_key),
        params={"filterByFormula": formula, "maxRecords": 1},
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"חיפוש רשומה #{serial} נכשל: {resp.status_code} {resp.text}")
    records = resp.json().get("records", [])
    return records[0]["id"] if records else None


def cmd_update_items(args):
    api_key, base_id = get_env()
    with open(args.updates_json, encoding="utf-8") as f:
        updates = json.load(f)

    if not updates:
        print(json.dumps({"error": "רשימת העדכונים ריקה"}, ensure_ascii=False))
        sys.exit(1)

    results = []
    for update in updates:
        serial = update["serial"]
        try:
            fields = build_update_fields(update)
            record_id = find_record_by_serial(api_key, base_id, serial)
        except (KeyError, ValueError, RuntimeError) as e:
            results.append({"serial": serial, "error": str(e)})
            continue

        if record_id is None:
            results.append({"serial": serial, "error": f"לא נמצאה רשומה עם מספר סידורי {serial}"})
            continue

        resp = requests.patch(
            f"{API_BASE}/{base_id}/{TABLE_ID}/{record_id}",
            headers=get_headers(api_key),
            json={"fields": fields},
            timeout=30,
        )
        if resp.status_code >= 400:
            results.append({"serial": serial, "error": f"עדכון נכשל: {resp.status_code} {resp.text}"})
            continue

        results.append({"serial": serial, "updated": True, "record_id": record_id, "fields": fields})

    failed = [r for r in results if "error" in r]
    print(json.dumps(
        {"results": results, "succeeded": len(results) - len(failed), "failed": len(failed)},
        ensure_ascii=False, indent=2,
    ))
    if failed:
        sys.exit(1)
```

Then update `main()` to add the second subcommand:

```python
def main():
    parser = argparse.ArgumentParser(description="Airtable content-calendar create+restricted-update (תכנון תוכן חודשי)")
    sub = parser.add_subparsers(dest="action", required=True)

    p_create = sub.add_parser("create-items", help="create new planned rows (status always מתוכנן)")
    p_create.add_argument("--items-json", required=True, help="JSON file: array of {week_or_date, channel, topic}")
    p_create.set_defaults(func=cmd_create_items)

    p_update = sub.add_parser("update-items", help="update status/note/final_link only, by מספר סידורי")
    p_update.add_argument("--updates-json", required=True, help="JSON file: array of {serial, status, note?, final_link?}")
    p_update.set_defaults(func=cmd_update_items)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace/.claude/skills/airtable-content-calendar/scripts" && python3 -m unittest test_content_calendar -v
```

Expected: `OK` — all tests pass (13 from Tasks 1-2 + 8 new = 21).

- [ ] **Step 5: Commit**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
git add .claude/skills/airtable-content-calendar/scripts/content_calendar.py .claude/skills/airtable-content-calendar/scripts/test_content_calendar.py
git commit -m "Add update-items CLI command to airtable-content-calendar"
```

---

### Task 4: `SKILL.md` for `airtable-content-calendar`

**Files:**
- Create: `.claude/skills/airtable-content-calendar/SKILL.md`

**Interfaces:**
- Consumes: the tested CLI from Tasks 1-3 (`create-items`, `update-items` subcommands and their exact `--items-json`/`--updates-json` flags).
- Produces: the doc that `yael.md` (Task 6) and `roi.md` (Task 8) point to for exact usage.

- [ ] **Step 1: Write the file**

Create `.claude/skills/airtable-content-calendar/SKILL.md`:

```markdown
---
name: airtable-content-calendar
description: מעטפת (wrapper) ליצירה ולעדכון מוגבל מאוד בטבלת "תכנון תוכן חודשי" ב-Airtable — מקור האמת ליומן תכנון-מול-ביצוע של התוכן. יצירה (create-items) משמשת את יעל (Yael) לזרוע פריטי תוכן כשהיא מסיימת תוכנית חודשית, תמיד עם סטטוס "מתוכנן". עדכון (update-items) מוגבל בקוד לשלושה שדות בלבד — סטטוס, הערה, קישור/גרסה סופית — ומזוהה לפי שדה ה-Autonumber "מספר סידורי", לא לפי מיקום ברשימה. רועי מפעיל את פעולת העדכון (דרך סוכן ה-catch-all, לא יעל) כשהמשתמשת עונה בצ'אט לתזכורת הדו-שבועית. דורש AIRTABLE_API_KEY ו-AIRTABLE_BASE_ID מוגדרים ב-.env (אותם משתנים כמו airtable-read/airtable-write). לעולם לא מוחק, לעולם לא נוגע בשדה אסטרטגיה (שבוע/ערוץ/נושא), לעולם לא בטבלה אחרת.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/content_calendar.py *)
---

# airtable-content-calendar — יצירה + עדכון מוגבל בטבלת "תכנון תוכן חודשי"

## עקרון מפתח: הרשאות מינימליות, שתי פעולות בלבד

| פעולה | מותר | אסור |
|---|---|---|
| **יצירה** (`create-items`) | שורה חדשה בטבלת "תכנון תוכן חודשי" (`tbl6S09qb9wK2ARW6`) בלבד, תמיד עם `סטטוס = מתוכנן` | כל טבלה אחרת, כל סטטוס אחר בזמן היצירה |
| **עדכון** (`update-items`) | **רק** השדות `סטטוס`, `הערה`, `קישור/גרסה סופית`, לפי `מספר סידורי` | שדות אסטרטגיה (`שבוע / תאריך יעד`, `ערוץ`, `נושא`), כל שדה אחר, מחיקה, `typecast` |

זהו הסקיל הראשון בפרויקט עם פעולת עדכון (PATCH), לא רק יצירה — ההגבלה לשלושה שדות ספציפיים אכופה **בקוד** (`build_update_fields` ב-`scripts/content_calendar.py`), לא רק בתיעוד כאן, באותה רוח שבה `airtable-write` מסרב במכוון ל-`typecast`.

## דרישות מקדימות

אותם משתני `.env` כמו ב-`airtable-read`/`airtable-write`:
- `AIRTABLE_API_KEY` — עם scope `data.records:read` **וגם** `data.records:write`.
- `AIRTABLE_BASE_ID`.
- `pip3 install requests` אם עוד לא מותקן.

**חד-פעמי, ידני, באיירטייבל עצמה** — לוודא שבטבלה "תכנון תוכן חודשי" (`tbl6S09qb9wK2ARW6`) קיימות העמודות הבאות, בדיוק בשם הזה (רגישות לרווחים/איות):

| עמודה | סוג |
|---|---|
| מספר סידורי | Autonumber |
| שבוע / תאריך יעד | Date |
| ערוץ | Single select: `בלוג`, `ניוזלטר`, `לינקדאין`, `פייסבוק/אינסטגרם`, `טיקטוק` |
| נושא | Long text |
| סטטוס | Single select: `מתוכנן`, `פורסם`, `שונה`, `לא עלה` |
| הערה | Long text |
| קישור/גרסה סופית | Long text |

אם עמודה חסרה או שהשם לא תואם בדיוק — קריאת יצירה/עדכון תיכשל עם `UNKNOWN_FIELD_NAME` או `INVALID_MULTIPLE_CHOICE_OPTIONS`; תקנו את שם/ערכי העמודה באיירטייבל, לא בקוד.

## יצירת פריטים (`create-items`)

קלט: קובץ JSON, מערך של אובייקטים `{week_or_date, channel, topic}`:

```bash
cat > /tmp/items.json <<'EOF'
[
  {"week_or_date": "2026-07-14", "channel": "בלוג", "topic": "5 סימנים שהעסק שלך צריך אוטומציית שיחות"},
  {"week_or_date": "2026-07-14", "channel": "לינקדאין", "topic": "תמצות המאמר לקהל מנהלי שיווק"}
]
EOF

python3 ${CLAUDE_SKILL_DIR}/scripts/content_calendar.py create-items --items-json /tmp/items.json
```

כל שורה נוצרת עם `סטטוס = מתוכנן` — אין אפשרות לקבוע סטטוס אחר ביצירה. הפלט כולל את `מספר סידורי` שהוקצה אוטומטית לכל שורה (שדה Autonumber של הטבלה עצמה) — אין צורך/אפשרות להמציא מזהה ידני.

## עדכון פריטים (`update-items`)

קלט: קובץ JSON, מערך של אובייקטים `{serial, status, note?, final_link?}` — `serial` הוא ערך `מספר סידורי` הקיים בטבלה, לא מיקום ברשימה:

```bash
cat > /tmp/updates.json <<'EOF'
[
  {"serial": 1, "status": "פורסם"},
  {"serial": 2, "status": "שונה", "note": "עשיתי גרסה אחרת לטיקטוק"},
  {"serial": 3, "status": "לא עלה"}
]
EOF

python3 ${CLAUDE_SKILL_DIR}/scripts/content_calendar.py update-items --updates-json /tmp/updates.json
```

`status` חייב להיות בדיוק אחד מ: `פורסם`, `שונה`, `לא עלה` (לעולם לא `מתוכנן` — זה ערך רק ליצירה). `note`/`final_link` אופציונליים — מדולגים אם ריקים.

## טיפול בשגיאות

- **`AIRTABLE_API_KEY`/`AIRTABLE_BASE_ID` חסרים** — הסקריפט מדפיס שגיאה וממשיך ב-exit code שאינו 0, בלי לנחש ערכים.
- **`מספר סידורי` לא נמצא** — מדווח כשגיאה עבור אותה שורה בלבד; שאר העדכונים בקבוצה ממשיכים (עדכון אחד לא תקין לא חוסם את השאר).
- **ערוץ/סטטוס לא מוכר** — נכשל **לפני** קריאת API כלשהי (ולידציה מקומית), בדיוק כמו שדות `singleSelect` ב-`airtable-write`.
- **שגיאת HTTP מה-API (`4xx`/`5xx`)** — גוף התגובה המלא מודפס לאבחון, אין ניחוש.

## מי מריץ את זה בפועל

- **`create-items`**: יעל (Yael), בסוף שלב שמירת התוכנית החודשית (ראו `.claude/agents/yael.md`, מצב א').
- **`update-items`**: **לא** יעל. רועי מזהה את תבנית התשובה הדו-שבועית של המשתמשת בצ'אט, ממפה אותה למספרים סידוריים, ומפעיל את סוכן ה-catch-all (לא אחד משבעת עובדי הצוות) להרצת הפעולה — ראו `.claude/agents/roi.md`, סעיף "עדכון סטטוס תוכן דו-שבועי". יעל היא שכבת אסטרטגיה וקריאת-היסטוריה, לא שכבת CRUD.
```

- [ ] **Step 2: Verify the skill's own doc references match the real CLI**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
grep -n "create-items\|update-items\|items-json\|updates-json" .claude/skills/airtable-content-calendar/SKILL.md .claude/skills/airtable-content-calendar/scripts/content_calendar.py
```

Expected: every flag name (`--items-json`, `--updates-json`) and subcommand name (`create-items`, `update-items`) appears identically in both files — no drift between doc and code.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/airtable-content-calendar/SKILL.md
git commit -m "Add SKILL.md for airtable-content-calendar"
```

---

### Task 5: Update `airtable-read/SKILL.md` (table description + pending-items query)

**Files:**
- Modify: `.claude/skills/airtable-read/SKILL.md`

**Interfaces:**
- No code interface — this is a documentation-only change. Later: the biweekly scheduled task (Task 11) and `roi.md` (Task 8) point readers here for the exact filter recipe.

- [ ] **Step 1: Update the table's one-line description in the table list**

In `.claude/skills/airtable-read/SKILL.md`, find this exact row in the "הטבלאות הידועות בבייס הזה" table:

```
| תכנון תוכן חודשי | `tbl6S09qb9wK2ARW6` | תוכנית/יומן תוכן חודשי קיים — לבדוק לפני בניית תוכנית חדשה |
```

Replace with:

```
| תכנון תוכן חודשי | `tbl6S09qb9wK2ARW6` | **מקור האמת הפעיל ליומן תכנון-מול-ביצוע** (ראו CLAUDE.md, "Feedback loop: plan vs. actual") — לבדוק לפני בניית תוכנית חדשה, וגם לקרוא פריטים ממתינים לעדכון סטטוס (ראו סעיף "שליפת פריטים ממתינים לעדכון סטטוס" למטה). כתיבה/עדכון בטבלה הזו דרך `airtable-content-calendar` בלבד, לא דרך הסקיל הזה |
```

- [ ] **Step 2: Add the pending-items query recipe**

Find this exact heading and the paragraph right after it:

```
## לא לשלוף הכל תמיד
```

Insert a new section immediately **before** that heading (i.e. right after the pagination section that precedes it):

```markdown
## שליפת פריטים ממתינים לעדכון סטטוס (לתזכורת הדו-שבועית)

עבור המשימה המתוזמנת `biweekly-content-feedback-email` (ראו `CLAUDE.md`, "Feedback loop: plan vs. actual", ו-`.claude/agents/roi.md`) — שליפת כל הרשומות בטבלת "תכנון תוכן חודשי" שסטטוסן עדיין `מתוכנן` ותאריך היעד שלהן כבר עבר:

```bash
today=$(date +%Y-%m-%d)
curl -s -G "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/tbl6S09qb9wK2ARW6" \
  --data-urlencode "filterByFormula=AND({סטטוס}='מתוכנן', IS_BEFORE({שבוע / תאריך יעד}, '$today'))" \
  --data-urlencode "fields[]=מספר סידורי" \
  --data-urlencode "fields[]=ערוץ" \
  --data-urlencode "fields[]=נושא" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" | jq '.records[] | {serial: .fields["מספר סידורי"], channel: .fields["ערוץ"], topic: .fields["נושא"]}'
```

אם התוצאה ריקה — אין פריטים ממתינים; המשימה המתוזמנת מדלגת על שליחת המייל בשקט (אין "בעיה" לדווח עליה).
```

- [ ] **Step 3: Verify the edit**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
grep -n "מקור האמת הפעיל\|שליפת פריטים ממתינים" .claude/skills/airtable-read/SKILL.md
```

Expected: both new strings found, in that order, before the existing "## לא לשלוף הכל תמיד" heading.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/airtable-read/SKILL.md
git commit -m "Document תכנון תוכן חודשי as the plan-vs-actual source of truth"
```

---

### Task 6: Update `.claude/agents/yael.md` (seeding + insights, tool scope, architectural note)

**Files:**
- Modify: `.claude/agents/yael.md`

**Interfaces:**
- No code interface — persona prompt changes only. Depends on Task 4's `SKILL.md` existing (referenced by path) and Task 3's exact CLI flags (referenced in prose).

- [ ] **Step 1: Update the `כלים` (Bash scope) section**

Find this exact paragraph:

```
`Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`.

**לא** `WebSearch`/`WebFetch`, **לא** `Agent`. בכוונה — בניגוד לליאת ולדני, את לא חוקרת באינטרנט. `Bash` שלך מוגבל **אך ורק** לשני שימושים:
1. הקריאות ב-`.claude/skills/airtable-read/SKILL.md` — קריאה בלבד (read-only) מכל טבלה רלוונטית בבייס האיירטייבל של הילה (הרשימה המלאה נמצאת בסקיל עצמו).
2. הרצת `.claude/skills/docx-export/scripts/md_to_docx.py` — כדי להמיר כל קובץ `.md` שאת שומרת ל-`.docx` תואם (ראו "שני מצבי עבודה" למטה).

**אסור** להשתמש ב-`Bash` לשום דבר אחר (לא כתיבה/עדכון לאיירטייבל, לא קריאה לכל API אחר, לא הרצת סקריפטים כלליים נוספים). מעבר לכך, את עובדת מהמסמכים הפנימיים של העסק (`yael/strategy.md` — שירותים, מסעות לקוח, חזון ויעדים) ומהתוצרים שהצוות כבר ייצר (`Content/`, `output/`, `dani/outputs/`, `merav/outputs/`), כדי שההמלצות שלך תמיד יהיו מעוגנות באסטרטגיה שהוגדרה בפועל ולא בניחוש/מחקר חיצוני.
```

Replace with:

```
`Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`.

**לא** `WebSearch`/`WebFetch`, **לא** `Agent`. בכוונה — בניגוד לליאת ולדני, את לא חוקרת באינטרנט. `Bash` שלך מוגבל **אך ורק** לשלושה שימושים:
1. הקריאות ב-`.claude/skills/airtable-read/SKILL.md` — קריאה בלבד (read-only) מכל טבלה רלוונטית בבייס האיירטייבל של הילה (הרשימה המלאה נמצאת בסקיל עצמו), כולל היסטוריית הסטטוסים בטבלת "תכנון תוכן חודשי" (ראו "תובנות מהיסטוריית תכנון-מול-ביצוע" במצב א' למטה).
2. הרצת `.claude/skills/docx-export/scripts/md_to_docx.py` — כדי להמיר כל קובץ `.md` שאת שומרת ל-`.docx` תואם (ראו "שני מצבי עבודה" למטה).
3. הרצת `python3 .claude/skills/airtable-content-calendar/scripts/content_calendar.py create-items ...` — **יצירה בלבד** של שורות חדשות בטבלת "תכנון תוכן חודשי", בסוף שלב שמירת תוכנית חודשית (ראו "זריעת פריטים ב-Airtable" במצב א' למטה).

**אסור** להשתמש ב-`Bash` לשום דבר אחר: לא הרצת פעולת `update-items` של אותו סקיל (עדכון סטטוס פריטים קיימים הוא **לא** תפקידך — ראו "⚠️ הערה ארכיטקטונית" למטה), לא כתיבה לאף טבלה אחרת חוץ מ"תכנון תוכן חודשי", לא קריאה לכל API אחר, לא הרצת סקריפטים כלליים נוספים. מעבר לכך, את עובדת מהמסמכים הפנימיים של העסק (`yael/strategy.md` — שירותים, מסעות לקוח, חזון ויעדים) ומהתוצרים שהצוות כבר ייצר (`Content/`, `output/`, `dani/outputs/`, `merav/outputs/`), כדי שההמלצות שלך תמיד יהיו מעוגנות באסטרטגיה שהוגדרה בפועל ולא בניחוש/מחקר חיצוני.
```

- [ ] **Step 2: Insert the insights-reading paragraph after step 3 of Mode A**

Find this exact line (step 3 of "מצב א'"):

```
3. קוראת (read-only, דרך סקיל `airtable-read`) את הטבלאות הרלוונטיות באיירטייבל — בעיקר `תכנון תוכן חודשי`, `מאגר תוכן קיים`, `מאגר תוכן - ניוזלטר`, ו-`תוכנית כלכלית חדש` אם רלוונטי — כדי לראות אילו פריטי תוכן כבר מתוכננים/פורסמו, ולא להציע דבר שכבר קיים שם.
```

Replace with (same line, plus a new standalone paragraph immediately after it):

```
3. קוראת (read-only, דרך סקיל `airtable-read`) את הטבלאות הרלוונטיות באיירטייבל — בעיקר `תכנון תוכן חודשי`, `מאגר תוכן קיים`, `מאגר תוכן - ניוזלטר`, ו-`תוכנית כלכלית חדש` אם רלוונטי — כדי לראות אילו פריטי תוכן כבר מתוכננים/פורסמו, ולא להציע דבר שכבר קיים שם.

**תובנות מהיסטוריית תכנון-מול-ביצוע:** בנוסף, קוראת (read-only, אותו סקיל `airtable-read`) את הרשומות מ-1 עד 3 החודשים האחרונים בטבלת `תכנון תוכן חודשי` (סטטוס `פורסם`/`שונה`/`לא עלה` + שדה ה`הערה`). אם מזהה דפוס חוזר — ערוץ/פורמט שחוזר ולא עולה, או שחוזר ומשתנה — מגבשת על כך 2-3 משפטים תחת כותרת "תובנות מהחודש/ים הקודמים" בתוכנית החדשה, ומשלבת זאת בנימוקי התדירות (שלב 5 למטה). אם אין עדיין רשומות עם סטטוס שאינו `מתוכנן` (למשל החודש הראשון של המנגנון) — מדלגת על השלב הזה בלי לציין זאת כבעיה. את **לא** אוצרת/כותבת תובנה כרשומה נפרדת באיירטייבל — זו הפקה חד-פעמית בפרוזה, בתוך התוכנית עצמה, לא שכבת אחסון נוספת (ראו "⚠️ הערה ארכיטקטונית" למטה).
```

- [ ] **Step 3: Insert the seeding paragraph after step 8 of Mode A**

Find this exact line (step 8 of "מצב א'"):

```
8. **תמיד** ממירה אותה גם ל-`.docx` תואם: `python3 .claude/skills/docx-export/scripts/md_to_docx.py yael/outputs/<YYYY-MM>-content-plan.md yael/outputs/<YYYY-MM>-content-plan.docx`. זו לא שלב אופציונלי — כל תוכנית תוכן חודשית יוצאת כזוג קבצים (md + docx), כמו הצמד md+html של נגה.
```

Replace with (same line, plus a new standalone paragraph immediately after it):

```
8. **תמיד** ממירה אותה גם ל-`.docx` תואם: `python3 .claude/skills/docx-export/scripts/md_to_docx.py yael/outputs/<YYYY-MM>-content-plan.md yael/outputs/<YYYY-MM>-content-plan.docx`. זו לא שלב אופציונלי — כל תוכנית תוכן חודשית יוצאת כזוג קבצים (md + docx), כמו הצמד md+html של נגה.

**זריעת פריטים ב-Airtable:** מיד לאחר מכן, יוצרת שורה אחת לכל פריט תוכן בתוכנית (למעט סטוריז אינסטגרם — לא נכללים בטבלה הזו, ראו `.claude/skills/airtable-content-calendar/SKILL.md`) בטבלת `תכנון תוכן חודשי`, דרך `python3 .claude/skills/airtable-content-calendar/scripts/content_calendar.py create-items --items-json <קובץ עם הפריטים>`. כל שורה נוצרת עם `סטטוס = מתוכנן` — זה הערך היחיד שאת קובעת; עדכון הסטטוס בהמשך (פורסם/שונה/לא עלה) **אינו** תפקידך (ראו "⚠️ הערה ארכיטקטונית" למטה).
```

- [ ] **Step 4: Update the final report step to mention the new row count**

Find this exact line (step 9 of "מצב א'"):

```
9. מדווחת לרועי: נתיבי שני הקבצים (md + docx) + התוכנית עצמה בתמצית ברורה, שמוכנה להעברה להילה.
```

Replace with:

```
9. מדווחת לרועי: נתיבי שני הקבצים (md + docx), כמה שורות נוצרו בטבלת "תכנון תוכן חודשי" (זריעה), ותקציר "תובנות מהחודש/ים הקודמים" אם הופק כזה + התוכנית עצמה בתמצית ברורה, שמוכנה להעברה להילה.
```

- [ ] **Step 5: Update "מה את יודעת" / "מה את לא יודעת"**

Find:

```
## מה את יודעת

לבנות תוכניות תוכן חודשיות מרובות-ערוצים (סושיאל/ניוזלטר/אתר) מבוססות אסטרטגיה, למפות נושא תוכן לשירות/שלב במסע לקוח/יעד, לזהות מתי דרוש מהלך אסטרטגי חדש לעומת תוכן שגרתי, להמליץ על סדר הפעלת עובדים לכל פריט תוכן, לקרוא (read-only) מכל טבלה רלוונטית בבייס האיירטייבל דרך `airtable-read`, לייצא כל תוכנית שהיא כותבת גם ל-`.docx` תואם דרך `docx-export`.

## מה את לא יודעת

לחפש באינטרנט, לכתוב או לשכתב תוכן, ליצור תמונות, לבצע SEO, לגשת ל-API חיצוני כלשהו מעבר לקריאה (read-only) מטבלאות האיירטייבל, לכתוב/לעדכן/למחוק דבר באיירטייבל, להפעיל סוכנים אחרים, לאשר/לפסול איכות של טיוטה כתובה.
```

Replace with:

```
## מה את יודעת

לבנות תוכניות תוכן חודשיות מרובות-ערוצים (סושיאל/ניוזלטר/אתר) מבוססות אסטרטגיה, למפות נושא תוכן לשירות/שלב במסע לקוח/יעד, לזהות מתי דרוש מהלך אסטרטגי חדש לעומת תוכן שגרתי, להמליץ על סדר הפעלת עובדים לכל פריט תוכן, לקרוא (read-only) מכל טבלה רלוונטית בבייס האיירטייבל דרך `airtable-read` (כולל היסטוריית תכנון-מול-ביצוע), לזרוע פריטי תוכנית חדשה (יצירה בלבד, סטטוס `מתוכנן`) בטבלת "תכנון תוכן חודשי" דרך `airtable-content-calendar`, לגבש תובנות מהיסטוריית סטטוסים לתכנון הבא, לייצא כל תוכנית שהיא כותבת גם ל-`.docx` תואם דרך `docx-export`.

## מה את לא יודעת

לחפש באינטרנט, לכתוב או לשכתב תוכן, ליצור תמונות, לבצע SEO, לגשת ל-API חיצוני כלשהו מעבר לקריאה (read-only) מטבלאות האיירטייבל ויצירה (create-only) בטבלת "תכנון תוכן חודשי", **לעדכן סטטוס פריטים קיימים באיירטייבל** (זו אחריות רועי + סוכן ה-catch-all, לא שלך), למחוק דבר באיירטייבל, להפעיל סוכנים אחרים, לאשר/לפסול איכות של טיוטה כתובה.
```

- [ ] **Step 6: Add a sentence to "⚠️ הערה ארכיטקטונית"**

Find:

```
## ⚠️ הערה ארכיטקטונית

את לא קוראת ישירות ל-`liat`/`dani`/`noga`/`merav` ולא לאף סוכן אחר. רועי הוא זה שמפעיל אותך (לתכנון חודשי או לבדיקת נושא), ואחר כך מעביר את ההנחיות/הפסיקה שלך לעובדים הרלוונטיים. כל התקשורת עוברת דרך רועי בלבד.
```

Replace with:

```
## ⚠️ הערה ארכיטקטונית

את לא קוראת ישירות ל-`liat`/`dani`/`noga`/`merav` ולא לאף סוכן אחר. רועי הוא זה שמפעיל אותך (לתכנון חודשי או לבדיקת נושא), ואחר כך מעביר את ההנחיות/הפסיקה שלך לעובדים הרלוונטיים. כל התקשורת עוברת דרך רועי בלבד.

באותה רוח: את **שכבת אסטרטגיה ולמידה** ביחס ליומן תכנון-מול-ביצוע, לא שכבת CRUD מול Airtable. את יוצרת שורות (`create-items`) וקוראת אותן בחזרה להפקת תובנות — אבל את **לא** מריצה אף פעם את `update-items`. עדכון סטטוס פריטים קיימים, לאחר שהמשתמשת מדווחת בצ'אט, מתבצע ע"י רועי + סוכן ה-catch-all (ראו `.claude/agents/roi.md`, "עדכון סטטוס תוכן דו-שבועי") — לא דרכך.
```

- [ ] **Step 7: Update the persona `description:` frontmatter**

Find this substring within the frontmatter `description:` line:

```
אין לה גישה כללית לאינטרנט/API; רק קריאה מוגבלת מהאיירטייבל, בתוספת ייצוא docx מקומי, בתוספת המסמכים הפנימיים והתוצרים הקיימים של הצוות.
```

Replace with:

```
אין לה גישה כללית לאינטרנט/API; רק קריאה מוגבלת מהאיירטייבל (כולל היסטוריית תכנון-מול-ביצוע), יצירה בלבד (לא עדכון) של שורות תכנון חדשות בטבלת "תכנון תוכן חודשי" דרך airtable-content-calendar, בתוספת ייצוא docx מקומי, בתוספת המסמכים הפנימיים והתוצרים הקיימים של הצוות.
```

- [ ] **Step 8: Verify all edits landed and no old text remains stale**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
grep -n "לשני שימושים\|לשלושה שימושים\|תובנות מהיסטוריית תכנון-מול-ביצוע\|זריעת פריטים ב-Airtable\|שכבת CRUD" .claude/agents/yael.md
```

Expected: `לשני שימושים` returns **no match** (fully replaced), `לשלושה שימושים` matches once, `תובנות מהיסטוריית תכנון-מול-ביצוע` matches twice (Mode A insertion + "מה את יודעת"), `זריעת פריטים ב-Airtable` matches once, `שכבת CRUD` matches once.

- [ ] **Step 9: Commit**

```bash
git add .claude/agents/yael.md
git commit -m "Wire Yael into the content feedback loop: seed items, read insights, never update"
```

---

### Task 7: Update `.claude/agents/_registry.yaml` (Yael's entry)

**Files:**
- Modify: `.claude/agents/_registry.yaml`

**Interfaces:**
- No code interface — registry metadata only.

- [ ] **Step 1: Update Yael's registry entry**

Find this exact block:

```yaml
  - id: yael
    status: active
    persona_path: .claude/agents/yael.md
    domain: strategic advisor
    capabilities:
      - monthly content planning
      - strategic-fit gate for new topics
    accepted_inputs:
      required: [period_to_plan, OR_topic_to_gate]
      optional: []
      implicit: [yael/strategy.md]
    produced_outputs:
      - path: "yael/outputs/<YYYY-MM>-content-plan.md"
        type: final
      - path: "yael/outputs/<YYYY-MM>-content-plan.docx"
        type: final
      - gate_verdict: [fits, needs_adjustment, new_strategic_move]
        type: domain_verdict
        note: "no file — a decision, not an artifact"
    typical_dependencies: []
    required_tools: [Read, Write, Edit, Glob, Grep, Bash]
    tool_scope_notes:
      Bash: "scoped to airtable-read (read-only) and docx-export only"
    optional_integrations: []
```

Replace with:

```yaml
  - id: yael
    status: active
    persona_path: .claude/agents/yael.md
    domain: strategic advisor
    capabilities:
      - monthly content planning
      - strategic-fit gate for new topics
      - plan-vs-actual item seeding (create-only, Airtable content calendar)
      - plan-vs-actual insight synthesis for the next monthly plan
    accepted_inputs:
      required: [period_to_plan, OR_topic_to_gate]
      optional: []
      implicit: [yael/strategy.md, "תכנון תוכן חודשי Airtable table (history)"]
    produced_outputs:
      - path: "yael/outputs/<YYYY-MM>-content-plan.md"
        type: final
      - path: "yael/outputs/<YYYY-MM>-content-plan.docx"
        type: final
      - gate_verdict: [fits, needs_adjustment, new_strategic_move]
        type: domain_verdict
        note: "no file — a decision, not an artifact"
      - airtable_rows: "one row per content item, status מתוכנן, in תכנון תוכן חודשי (tbl6S09qb9wK2ARW6)"
        type: final
        note: "create-only, via airtable-content-calendar — Yael never runs its update-items action"
    typical_dependencies: []
    required_tools: [Read, Write, Edit, Glob, Grep, Bash]
    tool_scope_notes:
      Bash: "scoped to airtable-read (read-only), docx-export, and airtable-content-calendar's create-items action only — never update-items"
    optional_integrations: []
```

- [ ] **Step 2: Verify the edit is valid YAML**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
python3 -c "import yaml; yaml.safe_load(open('.claude/agents/_registry.yaml'))" && echo "VALID YAML"
```

Expected: `VALID YAML` (no exception). If `yaml` module is missing, run `pip3 install pyyaml` first — this is a one-off validation step, not a new project dependency.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/_registry.yaml
git commit -m "Update Yael's registry entry with content-calendar seeding capability"
```

---

### Task 8: Update `.claude/agents/roi.md` (biweekly digest + chat-reply dispatch)

**Files:**
- Modify: `.claude/agents/roi.md`

**Interfaces:**
- Consumes: `airtable-content-calendar`'s `update-items` CLI (Task 3), `airtable-read`'s pending-items recipe (Task 5).
- No code interface produced — persona prompt only.

- [ ] **Step 1: Insert a new section between the weekly-email section and "תהליך העבודה"**

Find this exact line (the last line of the "מייל תוכנית שבועית" section, immediately before the "## תהליך העבודה" heading):

```
4. **שער האישור**: הפקת המייל וההמתנה קורים בסבב נפרד לגמרי מסבב האישור. כשהמשתמשת חוזרת בהמשך (בכל שיחה עתידית) ומאשרת את התוכנית לשבוע הבא (למשל "אישרתי", "אפשר להתחיל", "תתחילו על השבוע הבא") — זה הטריגר להתחיל בפועל: הפעל את `yael` כדי שתעביר לך את ההנחיות לביצוע פריטי אותו שבוע (מי מהעובדים ובאיזה סדר לכל פריט, לפי מה שכבר מוגדר בתוכנית), ואז המשך כרגיל לפי חיבורי הצוות הרגילים (`liat`→`noga`, `dani`↔`noga`, `noga`↔`merav`) לכל פריט. אם המשתמשת מבקשת שינויים לפני אישור — העבר את הבקשה ל-`yael` לעדכן את התוכנית, אל תפעיל עובדי ייצור על גרסה לא-מאושרת.

## תהליך העבודה (בכל בקשה, ללא יוצא מן הכלל)
```

Replace with (same two chunks, plus a new section inserted between them):

```
4. **שער האישור**: הפקת המייל וההמתנה קורים בסבב נפרד לגמרי מסבב האישור. כשהמשתמשת חוזרת בהמשך (בכל שיחה עתידית) ומאשרת את התוכנית לשבוע הבא (למשל "אישרתי", "אפשר להתחיל", "תתחילו על השבוע הבא") — זה הטריגר להתחיל בפועל: הפעל את `yael` כדי שתעביר לך את ההנחיות לביצוע פריטי אותו שבוע (מי מהעובדים ובאיזה סדר לכל פריט, לפי מה שכבר מוגדר בתוכנית), ואז המשך כרגיל לפי חיבורי הצוות הרגילים (`liat`→`noga`, `dani`↔`noga`, `noga`↔`merav`) לכל פריט. אם המשתמשת מבקשת שינויים לפני אישור — העבר את הבקשה ל-`yael` לעדכן את התוכנית, אל תפעיל עובדי ייצור על גרסה לא-מאושרת.

## עדכון סטטוס תוכן דו-שבועי (Feedback Loop)

זרימה קבועה נוספת, מופעלת ע"י ג'וב מתוזמן (`biweekly-content-feedback-email`) אחת לשבועיים — לא ע"י הודעה חופשית מהמשתמשת:

1. **הכנת התזכורת** (זה תפקידך): הג'וב קורא (read-only, `airtable-read`, ראו שם "שליפת פריטים ממתינים לעדכון סטטוס") את הרשומות בטבלת "תכנון תוכן חודשי" שסטטוסן עדיין `מתוכנן` ותאריך היעד שלהן כבר עבר, ומבקש ממך לנסח רשימה תמציתית וממוספרת **לפי `מספר סידורי` בפועל של כל רשומה** (לא לפי מיקום ברשימה). **ניסוח ניטרלי בכוונה** — "פריטים שמחכים לעדכון סטטוס ממך", **לעולם לא** "פריטים באיחור"/"בעיה" — המטרה לאסוף מידע קיים, לא ליצור תחושת חוב. אם אין רשומות כאלה — דווח זאת, הג'וב ידלג על שליחת המייל בשקט.
2. **אתה לא שולח את המייל בעצמך** — אותה מגבלה כמו במייל התוכנית השבועית: את הרשימה שהכנת אתה מחזיר כטקסט, והג'וב המתוזמן שולח אותה בפועל דרך `email-send`.
3. **עדכון בפועל (סבב נפרד לגמרי, בצ'אט חי)**: כשהמשתמשת חוזרת בהמשך עם עדכון בתבנית כמו "1-פורסם, 2-שונה (הערה חופשית), 3-לא עלה" — **אתה** (לא `yael`) ממפה כל מספר למזהה `מספר סידורי` המתאים (מתוך אותה רשימה ממוספרת שנשלחה), ומפעיל את סוכן ה-catch-all (לא אחד משבעת עובדי הצוות — זו פעולה טכנית סגורה, לא עבודת תוכן/אסטרטגיה) בבקשה להריץ:
   ```
   python3 .claude/skills/airtable-content-calendar/scripts/content_calendar.py update-items --updates-json <קובץ עם המיפוי>
   ```
   `<קובץ עם המיפוי>` הוא JSON: מערך של `{serial, status, note?, final_link?}`, בנוי מתוך המיפוי שביצעת. **`yael` אינה מעורבת בעדכון הטכני הזה בשום שלב** — היא רק קוראת את התוצאה בהמשך, בתכנון החודש הבא (ראו `.claude/agents/yael.md`, "תובנות מהיסטוריית תכנון-מול-ביצוע").
4. לאחר שהעדכון הצליח, אשר למשתמשת בקצרה אילו מספרים עודכנו לאיזה סטטוס. אם חלק מהעדכונים נכשלו (למשל מספר סידורי לא נמצא) — דווח בדיוק אילו, אל תציג הצלחה מלאה כשהיא חלקית.

## תהליך העבודה (בכל בקשה, ללא יוצא מן הכלל)
```

- [ ] **Step 2: Verify the insertion**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
grep -n "## עדכון סטטוס תוכן דו-שבועי\|## תהליך העבודה" .claude/agents/roi.md
```

Expected: the new heading appears once, immediately before "## תהליך העבודה" — confirming correct placement and that the section wasn't duplicated.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/roi.md
git commit -m "Add biweekly content-status digest flow to Roi"
```

---

### Task 9: Update `CLAUDE.md` (new section + tables)

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- No code interface — top-level project documentation only.

- [ ] **Step 1: Insert the new "Feedback loop" section after "Weekly plan email & approval gate"**

Find this exact paragraph (the last paragraph of that section, immediately before "## Architecture"):

```
Because Roi's own toolset stays orchestration-only (no `Bash`, no direct API/MCP access — see `.claude/agents/roi.md` for his exact tool grant and its scoping), the actual email send happens at the scheduling layer that invokes him, not inside Roi's persona — this was a deliberate choice to avoid widening his tool access for a single feature.

## Architecture
```

Replace with:

```
Because Roi's own toolset stays orchestration-only (no `Bash`, no direct API/MCP access — see `.claude/agents/roi.md` for his exact tool grant and its scoping), the actual email send happens at the scheduling layer that invokes him, not inside Roi's persona — this was a deliberate choice to avoid widening his tool access for a single feature.

## Feedback loop: plan vs. actual

Full design: [`docs/superpowers/specs/2026-07-15-content-feedback-loop-design.md`](docs/superpowers/specs/2026-07-15-content-feedback-loop-design.md). Closes the loop between Yael's monthly plans and what Hila actually publishes, changes, or skips, reusing the existing (previously idle) "תכנון תוכן חודשי" Airtable table (`tbl6S09qb9wK2ARW6`) as the single source of truth — no new database or dashboard.

When Yael finalizes a monthly plan, she also creates one row per content item (Instagram Stories excluded — they don't go through the full plan→create→publish flow) in that table via the `airtable-content-calendar` skill's create-only action, each starting at status `מתוכנן`. A recurring scheduled task (`biweekly-content-feedback-email`, every two weeks) reads rows still `מתוכנן` past their target date and asks Roi to draft a neutrally-worded digest ("items waiting for a status update," never "overdue"), sent via `email-send`. When Hila replies in a live chat (never by email reply — there's no inbox-reading capability, same constraint as the weekly plan email) with something like "1-published, 2-changed (did a different version), 3-didn't go up," Roi maps her reply to the table's own Autonumber field and dispatches the generic catch-all agent — deliberately not Yael, and not one of the seven roster employees — to run the skill's restricted update action, which can only ever touch the `סטטוס`/`הערה`/`קישור/גרסה סופית` fields. Yael stays a strategy-and-learning layer: she reads the accumulated history back in (never runs the update herself) when building the next monthly plan, and folds any recurring pattern (a channel/format that keeps getting skipped or changed) into that plan's frequency reasoning as inline prose — there is no separate stored "insight" record yet, by design (see the spec's "פערים מדעת" section for when that would change).

## Architecture
```

- [ ] **Step 2: Add the new skill row to the architecture table**

Find this exact row in the architecture table:

```
| `.claude/skills/airtable-write/SKILL.md` | Write wrapper for the Airtable REST API, deliberately narrow: create-only, one hardcoded table (existing-content, `tbl1eG92lW0vsY0tc`), never update/delete, never `typecast` (so an invalid `singleSelect` value fails loudly instead of inventing a new option) — used by Dani to log an article once the user confirms it's live |
```

Insert this new row immediately **after** it:

```
| `.claude/skills/airtable-content-calendar/SKILL.md` | Create + narrowly-restricted-update wrapper for the Airtable REST API, one hardcoded table ("תכנון תוכן חודשי", `tbl6S09qb9wK2ARW6`) — the plan-vs-actual source of truth. Create is used by Yael to seed a monthly plan's items (status always `מתוכנן`); update is restricted **in code** to exactly `סטטוס`/`הערה`/`קישור/גרסה סופית`, looked up by the table's own Autonumber field, and is run by the catch-all agent (dispatched by Roi), never by Yael — see "Feedback loop: plan vs. actual" above |
```

- [ ] **Step 3: Verify both edits**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
grep -n "## Feedback loop: plan vs. actual\|airtable-content-calendar/SKILL.md" CLAUDE.md
```

Expected: the new `##` heading appears once, and `airtable-content-calendar/SKILL.md` appears once in the architecture table, directly after the `airtable-write/SKILL.md` row.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "Document the content plan-vs-actual feedback loop in CLAUDE.md"
```

---

### Task 10: One-time Airtable setup + live smoke test (manual, requires confirmation)

**Files:** none (no repo files change in this task — it's operational verification against Hila's real Airtable base).

**⚠️ Do not run this task's commands without first confirming with Hila in chat.** It writes real (test) rows to her live "תכנון תוכן חודשי" table. `.env` in this repo already has `AIRTABLE_API_KEY`/`AIRTABLE_BASE_ID` set, so the script in Tasks 1-3 is technically able to reach her real base the moment it's run — that's exactly why this step is gated, not because credentials are missing.

- [ ] **Step 1: Confirm column setup with Hila**

Ask her to verify, in Airtable itself, that the "תכנון תוכן חודשי" table (`tbl6S09qb9wK2ARW6`) has all seven columns listed in `.claude/skills/airtable-content-calendar/SKILL.md`'s "דרישות מקדימות" section, with an Autonumber field named exactly `מספר סידורי`. Do not proceed to Step 2 until she confirms.

- [ ] **Step 2: Refresh the live schema via the Metadata API (read-only, safe to run anytime)**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
source .env 2>/dev/null || export $(grep -v '^#' .env | xargs)
curl -s "https://api.airtable.com/v0/meta/bases/$AIRTABLE_BASE_ID/tables" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" | \
  python3 -c "import json,sys; t=json.load(sys.stdin)['tables']; m=[x for x in t if x['id']=='tbl6S09qb9wK2ARW6'][0]; print([f['name'] for f in m['fields']])"
```

Expected output: a Python list containing exactly `מספר סידורי`, `שבוע / תאריך יעד`, `ערוץ`, `נושא`, `סטטוס`, `הערה`, `קישור/גרסה סופית` (order doesn't matter). If any are missing, stop and have Hila add them before continuing.

- [ ] **Step 3: Live smoke test — create one throwaway item**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
cat > /tmp/smoke-test-items.json <<'EOF'
[{"week_or_date": "2026-01-01", "channel": "בלוג", "topic": "SMOKE TEST - delete me"}]
EOF
python3 .claude/skills/airtable-content-calendar/scripts/content_calendar.py create-items --items-json /tmp/smoke-test-items.json
```

Expected: JSON output with `"created": 1` and a `records` array containing one record with a real `id` (starts with `rec`) and a `מספר סידורי` value. **Note the `מספר סידורי` value** — it's needed for Step 4.

- [ ] **Step 4: Live smoke test — update that same item, then confirm restricted fields**

```bash
cd "/Users/hilaganani/Documents/workspace/hilas-workspace"
cat > /tmp/smoke-test-updates.json <<'EOF'
[{"serial": <the מספר סידורי value from Step 3>, "status": "פורסם", "note": "smoke test note"}]
EOF
python3 .claude/skills/airtable-content-calendar/scripts/content_calendar.py update-items --updates-json /tmp/smoke-test-updates.json
```

Expected: JSON output with `"succeeded": 1`, `"failed": 0`. Then open the record in Airtable directly and confirm only `סטטוס` and `הערה` changed — `ערוץ`/`נושא`/`שבוע / תאריך יעד` are untouched.

- [ ] **Step 5: Clean up the throwaway row**

Tell Hila the `מספר סידורי` value of the smoke-test row and ask her to delete it manually in Airtable (this skill deliberately has no delete capability, per Global Constraints — that's not an oversight to work around here).

---

### Task 11: Create the `biweekly-content-feedback-email` scheduled task (requires confirmation)

**Files:** none (creates a task via the `create_scheduled_task` tool, stored outside this repo per that tool's own description — `{taskId}/SKILL.md` under the user's Claude Code config directory, not under this project).

**⚠️ Do not call `create_scheduled_task` without confirming with Hila first**, even though the tool itself shows its own approval dialog — this creates a standing, recurring automation that emails her every two weeks.

- [ ] **Step 1: Decide the cron cadence**

Standard 5-field cron (what `create_scheduled_task` accepts) has no native "every 14 days" primitive. Use the same weekly trigger as `weekly-content-plan-email` (`0 7 * * 4`, Thursday 7am local) and have the task's own prompt check ISO week parity so it only proceeds on every other Thursday — stateless, no extra storage needed:

```python
import datetime
iso_week = datetime.date.today().isocalendar()[1]
run_this_week = (iso_week % 2 == 0)  # fixed parity, arbitrary but consistent
```

- [ ] **Step 2: Call `create_scheduled_task`**

```
taskId: "biweekly-content-feedback-email"
description: "Every two weeks: digest of תכנון תוכן חודשי items still מתוכנן past their target date, asks Roi to draft it, sends via email-send"
cronExpression: "0 7 * * 4"
prompt: |
  זהו ריצה של המשימה המתוזמנת biweekly-content-feedback-email (ראו CLAUDE.md,
  "Feedback loop: plan vs. actual", ו-.claude/agents/roi.md, "עדכון סטטוס תוכן דו-שבועי").

  1. חשב את מספר השבוע ה-ISO של היום (datetime.date.today().isocalendar()[1]).
     אם הוא אי-זוגי — עצור כאן, אל תמשיך (זו הפעימה השבועית ה"ריקה" מתוך המחזור הדו-שבועי).
  2. אם זוגי: קרא (read-only, .claude/skills/airtable-read/SKILL.md, סעיף "שליפת
     פריטים ממתינים לעדכון סטטוס") את הרשומות ב"תכנון תוכן חודשי" (tbl6S09qb9wK2ARW6)
     שסטטוסן `מתוכנן` ותאריך היעד שלהן עבר.
  3. אם אין רשומות כאלה — עצור בשקט, אל תשלח מייל.
  4. אם יש — הפעל את roi (Agent tool) עם הבקשה לנסח תזכורת תמציתית, ממוספרת לפי
     `מספר סידורי` בפועל, בניסוח ניטרלי ("פריטים שמחכים לעדכון סטטוס", לעולם לא
     "באיחור"/"בעיה"). roi מוגבל כאן לניסוח בלבד — אל תיתן לו להפעיל liat/dani/
     noga/merav מהריצה הזו.
  5. עצב את התמצית ל-HTML פשוט ושלח דרך .claude/skills/email-send/SKILL.md
     ל-PLAN_EMAIL_TO (מ-.env).
notifyOnCompletion: false
```

- [ ] **Step 3: Verify the task was created**

Use `mcp__scheduled-tasks__list_scheduled_tasks` (or ask the user to check) and confirm `biweekly-content-feedback-email` appears with the cron expression from Step 2.

---

## Self-Review Notes

- **Spec coverage:** §5 (data model) → Tasks 1, 4, 10 (SKILL.md documents the columns; Task 10 verifies them live). §6 (skill) → Tasks 1-4. §7 flow A (seeding) → Task 6 Steps 3/4. §7 flow B (biweekly reminder) → Tasks 5, 8, 11. §7 flow C (chat update) → Tasks 8, 3. §7 flow D (insights) → Task 6 Step 2. §8 (key decisions, incl. the user's "Yael is out of the CRUD path" correction) → Tasks 6, 8 both reflect this explicitly. §9 (deliberate gaps) → documented in CLAUDE.md (Task 9) and left unbuilt, matching the spec.
- **Placeholder scan:** no TBD/TODO; every code step has complete, runnable code; every doc step has exact copy-pasteable text.
- **Type/name consistency checked across tasks:** `create-items`/`--items-json` and `update-items`/`--updates-json` (Tasks 2-3) match exactly in `SKILL.md` (Task 4), `yael.md` (Task 6), and `roi.md` (Task 8). Field names (`סטטוס`, `הערה`, `קישור/גרסה סופית`, `מספר סידורי`, `שבוע / תאריך יעד`, `ערוץ`, `נושא`) are identical across the script, both persona files, and the design spec.
