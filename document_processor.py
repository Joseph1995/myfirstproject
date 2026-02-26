"""
Document processor — extract plain text from PDF, Word, Excel, PowerPoint, and images.

Supported extensions:
  PDF   : .pdf  (via pypdf)
  Word  : .docx, .doc  (via python-docx)
  Excel : .xlsx, .xls  (via openpyxl)
  PPT   : .pptx, .ppt  (via python-pptx)
  Image : .png, .jpg, .jpeg, .gif, .bmp, .tiff, .tif, .webp  (via pytesseract + Pillow)
"""

import os


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file using pypdf."""
    try:
        import pypdf

        pages = []
        with open(filepath, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n".join(pages)
    except Exception as exc:
        return f"[Error reading PDF: {exc}]"


def extract_text_from_docx(filepath: str) -> str:
    """Extract text from a Word document (.docx)."""
    try:
        from docx import Document

        doc = Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text.strip())
        return "\n".join(paragraphs)
    except Exception as exc:
        return f"[Error reading DOCX: {exc}]"


def extract_text_from_xlsx(filepath: str) -> str:
    """Extract text from an Excel workbook (.xlsx / .xls)."""
    try:
        import openpyxl

        wb = openpyxl.load_workbook(filepath, data_only=True)
        lines = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            lines.append(f"[Sheet: {sheet_name}]")
            for row in ws.iter_rows(values_only=True):
                row_text = " | ".join(
                    str(cell) for cell in row if cell is not None
                )
                if row_text.strip():
                    lines.append(row_text)
        return "\n".join(lines)
    except Exception as exc:
        return f"[Error reading XLSX: {exc}]"


def extract_text_from_pptx(filepath: str) -> str:
    """Extract text from a PowerPoint presentation (.pptx / .ppt)."""
    try:
        from pptx import Presentation

        prs = Presentation(filepath)
        text = []
        for i, slide in enumerate(prs.slides, 1):
            text.append(f"[Slide {i}]")
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    text.append(shape.text.strip())
        return "\n".join(text)
    except Exception as exc:
        return f"[Error reading PPTX: {exc}]"


def extract_text_from_image(filepath: str) -> str:
    """Extract text from an image via OCR (requires pytesseract + tesseract)."""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(filepath)
        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else "[Image: no text detected by OCR]"
    except ImportError:
        return (
            "[Image OCR skipped: install pytesseract and the tesseract binary to"
            " extract text from images]"
        )
    except Exception as exc:
        return f"[Error reading image: {exc}]"

def _legacy_format_unsupported(filepath: str) -> str:
    """Return a helpful message for legacy Office formats that cannot be read."""
    ext = os.path.splitext(filepath)[1].lower()
    modern = {".doc": ".docx", ".xls": ".xlsx", ".ppt": ".pptx"}
    modern_ext = modern.get(ext, ext)
    return (
        f"[Legacy {ext} format is not supported for text extraction. "
        f"Please convert the file to {modern_ext} and re-upload.]"
    )


_HANDLERS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".doc": _legacy_format_unsupported,
    ".xlsx": extract_text_from_xlsx,
    ".xls": _legacy_format_unsupported,
    ".pptx": extract_text_from_pptx,
    ".ppt": _legacy_format_unsupported,
    ".png": extract_text_from_image,
    ".jpg": extract_text_from_image,
    ".jpeg": extract_text_from_image,
    ".gif": extract_text_from_image,
    ".bmp": extract_text_from_image,
    ".tiff": extract_text_from_image,
    ".tif": extract_text_from_image,
    ".webp": extract_text_from_image,
}

SUPPORTED_EXTENSIONS = set(_HANDLERS.keys())


def process_document(filepath: str) -> str:
    """Dispatch extraction based on the file's extension."""
    ext = os.path.splitext(filepath)[1].lower()
    handler = _HANDLERS.get(ext)
    if handler is None:
        return f"[Unsupported file type: {ext}]"
    return handler(filepath)
