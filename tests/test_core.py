import unittest
from unittest.mock import patch

from app.collection.manager import parse_period
from app.downloader.downloader import find_month_candidates
from app.extractors.report_extractor import ReportExtractor
from app.extractors.table_extractor import TableExtractor


class CoreTests(unittest.TestCase):
    def test_parse_period(self):
        self.assertEqual(parse_period("Июль 2026"), (7, 2026))
        self.assertEqual(parse_period("Сентябрь 2026"), (9, 2026))

    def test_parse_period_rejects_invalid_month(self):
        with self.assertRaises(ValueError):
            parse_period("Новый 2026")

    def test_find_month_candidates_uses_year_heading(self):
        html = """
        <h2>2025</h2><a href="old.pdf">Июль</a>
        <h2>2026</h2><a href="new.pdf">Июль</a>
        """
        result = find_month_candidates(
            html,
            "https://example.test/reports/",
            7,
            2026,
        )
        self.assertEqual(result, [(
            "https://example.test/reports/new.pdf",
            "Июль",
            True,
        )])

    def test_intermediate_links_require_month_and_year(self):
        html = """
        <a href="report-2025.pdf">Июль 2025</a>
        <a href="report-2026.pdf">Июль 2026</a>
        <a href="all-reports.pdf">Все отчёты</a>
        """
        from app.downloader.downloader import collect_period_file_links

        result = collect_period_file_links(
            html,
            "https://example.test/",
            7,
            2026,
        )
        self.assertEqual(result, [("https://example.test/report-2026.pdf", "Июль 2026")])

    def test_number_parsers(self):
        self.assertEqual(ReportExtractor.clean_number("(2 043 879)"), -2043879)
        self.assertEqual(TableExtractor.parse_number("-2 043 879"), -2043879)

    def test_empty_ratio_pages(self):
        self.assertEqual(TableExtractor().extract_ratios([]), {})

    @patch("app.collection.manager.process_bank")
    def test_collection_manager_processes_all_banks(self, process_bank):
        from app.collection.manager import CollectionManager

        manager = CollectionManager()
        output_root, manual_checks = manager.start("Июль 2026")

        self.assertEqual(output_root, "data/input")
        self.assertEqual(manual_checks, [])
        self.assertEqual(process_bank.call_count, len(manager.banks))


if __name__ == "__main__":
    unittest.main()
