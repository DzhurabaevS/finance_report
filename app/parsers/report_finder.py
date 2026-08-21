import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path

print("REPORT FINDER ЗАПУЩЕН") 
class ReportFinder:
    def __init__(self):
        self.headers = {
             "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/148.0 Safari/537.36"
            )
            }

    def get_page(self, url):
        response = requests.get(
            url,
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()

        return response.text

    def find_report(self, page_url, report_name):
        html = self.get_page(page_url)

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        links = soup.find_all("a")

        for link in links:
            text = link.get_text(
                " ",
                strip = True
            )
            if report_name.lower() in text.lower():
                href = link.get("href")

                if href:
                    return urljoin(
                        page_url,
                        href
                    )

        return None

    def download_report(self, report_url, save_path):
        response = requests.get(
            report_url,
            headers=self.headers,
            timeout=60
        )

        response.raise_for_status()

        save_path = Path(save_path)
        save_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        save_path.write_bytes(response.content)

        return save_path

if __name__ == "__main__":
    print("НАЧАЛО ТЕСТА")

    finder = ReportFinder()

    page_url = "https://kicb.net/about/financial-reporting/2026/"

    report_url = finder.find_report(
        page_url,
        "Июль 2026 года"
    )

    print("Найденный файл:")
    print(report_url)

    if report_url:
        finder.download_report(
            report_url,
            "kicb_july_2026.pdf"
        )