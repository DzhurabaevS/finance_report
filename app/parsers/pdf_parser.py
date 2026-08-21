
import pymupdf
import pytesseract
from PIL import Image
import io
import os

print("PDF parser запущен")

class PDFParser:
    def __init__(self):
        self.tesseract_path = os.environ.get(
            "TESSERACT_CMD",
            r"C:\Users\sdzhurabaev\AppData\Local\Tesseract-OCR\tesseract.exe",
        )
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def extract_text(self, pdf_path):
        with pymupdf.open(pdf_path) as document:
            text = "".join(page.get_text() for page in document)

            if len(text.strip()) >= 100:
                return text

            print("текст не найден")
            ocr_text = []
            for page_number, page in enumerate(document):
                print(f"OCR страницы {page_number + 1}...")
                pix = page.get_pixmap(dpi=300)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text.append(
                    pytesseract.image_to_string(image, lang="rus+eng")
                )

            return "\n".join(ocr_text)

if __name__ == "__main__":
    print("Started")

    parser = PDFParser()
    pdf_path = r"D:\dzhurabaev\finance_report\kicb_july_2026.pdf"

    text = parser.extract_text(pdf_path)

    with open(
        "ocr_text.txt",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(text)

    print("Текст сохранён в ocr_text.txt")

    print("Первые 5000 символов:")
    print(text[:5000])