from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from craw_real_times.extractor.article import ArticleExtractor, _parse_datetime_text


class RelativeTimeParsingTests(unittest.TestCase):
    def assertAgo(self, text: str, expected: timedelta) -> None:
        parsed = _parse_datetime_text(text)
        self.assertIsNotNone(parsed)
        actual = datetime.now(timezone.utc) - parsed
        self.assertLess(abs(actual - expected), timedelta(seconds=5), text)

    def test_relative_times_subtract_from_now(self) -> None:
        self.assertAgo("55 phút trước", timedelta(minutes=55))
        self.assertAgo("12 phút trước", timedelta(minutes=12))
        self.assertAgo("1 giờ trước", timedelta(hours=1))
        self.assertAgo("3 tiếng trước", timedelta(hours=3))
        self.assertAgo("1 ngày trước", timedelta(days=1))
        self.assertAgo("2 tuần trước", timedelta(weeks=2))
        self.assertAgo("Cập nhật 30 giây trước", timedelta(seconds=30))
        self.assertAgo("5 Phút Trước", timedelta(minutes=5))
        self.assertAgo("10 phut truoc", timedelta(minutes=10))

    def test_absolute_dates_parse(self) -> None:
        cases = {
            "Thứ năm, 25/9/2026 | 14:30": datetime(2026, 9, 25, 14, 30),
            "Hồ Thảo 13:13, 25/09/2026 chia sẻ": datetime(2026, 9, 25, 13, 13),
            "- 25/09/2026 08:34": datetime(2026, 9, 25, 8, 34),
            "01:02 PM 01/09/2026": datetime(2026, 9, 1, 13, 2),
            "Thứ Bảy, ngày 01 tháng 3 năm 2025": datetime(2025, 3, 1),
            "2026-09-09T07:27:00": datetime(2026, 9, 9, 7, 27),
            "10/09/2026": datetime(2026, 9, 10),
        }
        for text, expected in cases.items():
            self.assertEqual(_parse_datetime_text(text), expected, text)

    def test_text_without_explicit_date_is_ignored(self) -> None:
        for text in ("00:00", "Lượt xem: 2040", "Chia sẻ 1037", "14:55", "25/09/2055 10:00", "31/02/2026"):
            self.assertIsNone(_parse_datetime_text(text), text)


class PublishDateElementTests(unittest.TestCase):
    def test_header_clock_and_player_timer_are_skipped(self) -> None:
        html = """
        <html><body>
          <header><span class="date">Thứ sáu, 25/9/2026</span></header>
          <span class="time-now">Thứ sáu, 25/9/2026</span>
          <span class="podcast-audio-player__time">00:00</span>
          <span class="date">Thứ năm, 24/9/2026, 10:31 (GMT+7)</span>
        </body></html>
        """
        extractor = ArticleExtractor("https://example.com/story-1.html")
        self.assertEqual(
            extractor._extract_publish_date(BeautifulSoup(html, "html.parser")),
            datetime(2026, 9, 24, 10, 31),
        )

    def test_meta_name_article_published_time_is_read(self) -> None:
        html = '<html><head><meta name="article:published_time" content="2026-09-25T08:00:38+07:00"></head></html>'
        extractor = ArticleExtractor("https://example.com/story-1.html")
        self.assertEqual(
            extractor._extract_publish_date(BeautifulSoup(html, "html.parser")),
            datetime(2026, 9, 25, 1, 0, 38, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
