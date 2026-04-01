import unittest

from wps_archive.title_parser import parse_meeting_title


class TitleParserTests(unittest.TestCase):
    def test_parses_single_name(self):
        parsed = parse_meeting_title("栾天成_毕业设计", exclude_people=["沈惠中"])
        self.assertEqual(parsed.suggested_people_names, ["栾天成"])
        self.assertEqual(parsed.suggested_topic, "毕业设计")
        self.assertFalse(parsed.needs_confirmation)
        self.assertTrue(parsed.has_structured_title)

    def test_parses_multiple_names(self):
        parsed = parse_meeting_title("栾天成、褚梦圆_臭氧反演", exclude_people=["沈惠中"])
        self.assertEqual(parsed.suggested_people_names, ["栾天成", "褚梦圆"])
        self.assertEqual(parsed.suggested_topic, "臭氧反演")
        self.assertFalse(parsed.needs_confirmation)
        self.assertTrue(parsed.has_structured_title)

    def test_excludes_mentor(self):
        parsed = parse_meeting_title("沈惠中、栾天成_毕业设计", exclude_people=["沈惠中"])
        self.assertEqual(parsed.suggested_people_names, ["栾天成"])
        self.assertEqual(parsed.suggested_topic, "毕业设计")
        self.assertFalse(parsed.needs_confirmation)
        self.assertTrue(parsed.has_structured_title)

    def test_missing_separator_needs_confirmation(self):
        parsed = parse_meeting_title("毕业设计讨论", exclude_people=["沈惠中"])
        self.assertEqual(parsed.suggested_people_names, [])
        self.assertEqual(parsed.suggested_topic, "毕业设计讨论")
        self.assertTrue(parsed.needs_confirmation)
        self.assertFalse(parsed.has_structured_title)

    def test_empty_right_side_is_not_structured(self):
        parsed = parse_meeting_title("栾天成_", exclude_people=["沈惠中"])
        self.assertEqual(parsed.suggested_people_names, ["栾天成"])
        self.assertFalse(parsed.has_structured_title)


if __name__ == "__main__":
    unittest.main()
