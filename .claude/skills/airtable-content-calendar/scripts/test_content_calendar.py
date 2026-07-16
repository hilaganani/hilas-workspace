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
    find_record_by_serial,
    cmd_update_items,
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


if __name__ == "__main__":
    unittest.main()
