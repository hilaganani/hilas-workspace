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
