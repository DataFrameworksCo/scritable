from typing import List


def parse_file(file_obj, filename: str) -> List[str]:
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext == 'txt':
        return _parse_txt(file_obj)
    elif ext == 'docx':
        return _parse_docx(file_obj)
    elif ext == 'pdf':
        return _parse_pdf(file_obj)
    raise ValueError(f"Unsupported file type: .{ext}")


def _parse_txt(file_obj) -> List[str]:
    content = file_obj.read().decode('utf-8', errors='replace')
    blocks = content.split('\n\n')
    return [b.replace('\n', ' ').strip() for b in blocks if b.strip()]


def _parse_docx(file_obj) -> List[str]:
    from docx import Document
    doc = Document(file_obj)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def _parse_pdf(file_obj) -> List[str]:
    import pdfplumber
    paragraphs = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for block in text.split('\n\n'):
                    clean = block.replace('\n', ' ').strip()
                    if clean:
                        paragraphs.append(clean)
    return paragraphs
