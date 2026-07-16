import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from content_calendar import (
    ALLOWED_CHANNELS,
    ALLOWED_STATUSES,
    DEFAULT_STATUS,
    build_create_fields,
    build_update_fields,
    chunked,
    cmd_create_items,
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


if __name__ == "__main__":
    unittest.main()
