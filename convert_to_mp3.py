import sys
import io
import time
import subprocess
from pathlib import Path
from gtts import gTTS
from gtts.tts import gTTSError
from docx import Document

from ocr.groq_engine import ocr_full_text


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def ocr_image(input_path: Path) -> str:
    """Groq vision trước (đồng nhất với /obituary, /ocr...); lỗi/thiếu GROQ_API_KEY thì
    fallback về tesseract (chất lượng kém hơn với chữ viết tay nhưng không phụ thuộc mạng)."""
    try:
        print(f"  Nhận dạng chữ từ ảnh (Groq vision)...")
        text = ocr_full_text(input_path.read_bytes())
        if text.strip():
            return text
        print(f"  [Groq trả rỗng] fallback tesseract...")
    except Exception as e:
        print(f"  [Groq lỗi: {e}] fallback tesseract...")

    result = subprocess.run(
        ["tesseract", str(input_path), "stdout", "-l", "vie+eng", "--psm", "3"],
        capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout


def extract_text(input_path: Path) -> str:
    suffix = input_path.suffix.lower()
    if suffix == ".txt":
        return input_path.read_text(encoding="utf-8")
    elif suffix in IMAGE_EXTS:
        text = ocr_image(input_path)
        if not text or not text.strip():
            raise ValueError(
                f"Không nhận dạng được chữ từ ảnh '{input_path.name}'. "
                "Hãy chắc chắn ảnh rõ nét và có chữ."
            )
        return text
    elif suffix in (".docx", ".doc"):
        doc = Document(str(input_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif suffix == ".pdf":
        # Kiểm tra magic bytes — file thật phải bắt đầu bằng %PDF
        with open(str(input_path), 'rb') as fh:
            header = fh.read(5)
        if not header.startswith(b'%PDF'):
            if header.startswith(b'<!'):
                raise ValueError(
                    f"File '{input_path.name}' là HTML (có thể bạn tải nhầm trang đăng nhập Google Drive). "
                    "Hãy tải lại file PDF gốc và upload lại."
                )
            raise ValueError(
                f"File '{input_path.name}' không phải PDF hợp lệ (header: {header!r})"
            )
        result = subprocess.run(
            ["pdftotext", str(input_path), "-"],
            capture_output=True, text=True, encoding="utf-8"
        )
        text = result.stdout
        if text and text.strip():
            return text
        # PDF scanned (ảnh) → dùng OCR
        print(f"  PDF không có text layer, thử OCR (tesseract)...")
        ocr_out = Path(str(input_path) + "_ocr.pdf")
        subprocess.run(
            ["ocrmypdf", "--language", "vie+eng", "--force-ocr",
             str(input_path), str(ocr_out)],
            capture_output=True
        )
        if ocr_out.exists():
            result2 = subprocess.run(
                ["pdftotext", str(ocr_out), "-"],
                capture_output=True, text=True, encoding="utf-8"
            )
            ocr_out.unlink(missing_ok=True)
            text2 = result2.stdout
            if text2 and text2.strip():
                return text2
        raise ValueError(f"Không đọc được nội dung từ PDF (cả OCR): {input_path.name}")
    else:
        raise ValueError(f"Định dạng không được hỗ trợ: {suffix} (chỉ hỗ trợ .txt, .docx, .pdf)")


def split_text(text: str, max_chars: int = 3000) -> list[str]:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if not current:
            current = para
        elif len(current) + len(para) + 2 <= max_chars:
            current += "\n\n" + para
        else:
            chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def chunk_to_mp3_bytes(text: str, lang: str, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()
        except gTTSError as e:
            if '429' in str(e) and attempt < retries - 1:
                wait = 60 * (attempt + 1)
                print(f"  [429] Rate limited, chờ {wait}s rồi thử lại...")
                time.sleep(wait)
            else:
                raise


def convert_to_mp3(input_file: str, output_dir: str = "output", lang: str = "vi"):
    input_path = Path(input_file)

    if not input_path.parent.name or input_path.parent == Path("."):
        input_path = Path("data") / input_path

    if not input_path.exists():
        raise FileNotFoundError(f"File không tồn tại: {input_path}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Đang đọc: {input_path.name}")
    text = extract_text(input_path)

    chunks = split_text(text, max_chars=3000)
    total = len(chunks)
    print(f"Tổng số đoạn: {total} (~{len(text)} ký tự)")

    output_file = output_path / (input_path.stem + ".mp3")

    with open(str(output_file), 'wb') as outf:
        for i, chunk in enumerate(chunks, 1):
            if (i - 1) % 20 == 0 or i == total:
                print(f"  Đoạn {i}/{total}...")
            data = chunk_to_mp3_bytes(chunk, lang)
            outf.write(data)
            time.sleep(1.0)

    size_mb = output_file.stat().st_size / 1024 / 1024
    print(f"Đã lưu: {output_file} ({size_mb:.1f} MB)")
    return output_file


def convert_all_in_folder(data_dir: str = "data", output_dir: str = "output", lang: str = "vi"):
    data_path = Path(data_dir)
    files = (list(data_path.glob("*.txt")) +
             list(data_path.glob("*.docx")) +
             list(data_path.glob("*.pdf")))

    if not files:
        print(f"Không tìm thấy file nào trong: {data_dir}")
        return

    print(f"Tìm thấy {len(files)} file")
    for f in files:
        convert_to_mp3(str(f), output_dir, lang)

    print("Hoàn thành!")


def convert_multi_images(image_files: list, output_stem: str, output_dir: str = "output", lang: str = "vi"):
    """OCR nhiều ảnh theo thứ tự, ghép text → 1 MP3, đồng thời tạo PDF tổng hợp."""
    from PIL import Image as PILImage

    resolved = []
    for img_file in image_files:
        p = Path(img_file)
        if not p.parent.name or p.parent == Path("."):
            p = Path("data") / p
        if not p.exists():
            raise FileNotFoundError(f"File không tồn tại: {p}")
        resolved.append(p)

    # 1. Tạo PDF ghép ảnh (giữ đúng thứ tự)
    pdf_dir = Path("pdfs")
    pdf_dir.mkdir(exist_ok=True)
    pdf_path = pdf_dir / f"{output_stem}.pdf"
    print(f"  Ghép {len(resolved)} ảnh → PDF...")
    pil_imgs = [PILImage.open(str(p)).convert("RGB") for p in resolved]
    pil_imgs[0].save(
        str(pdf_path), save_all=True, append_images=pil_imgs[1:], resolution=150
    )
    print(f"  PDF: {pdf_path}")

    # 2. OCR từng ảnh (đúng thứ tự)
    texts = []
    for p in resolved:
        print(f"  OCR ảnh: {p.name}")
        t = ocr_image(p).strip()
        if t:
            texts.append(t)
        else:
            print(f"  [cảnh báo] Không nhận dạng được chữ từ: {p.name}")

    if not texts:
        raise ValueError("Không nhận dạng được chữ từ bất kỳ ảnh nào.")

    combined = "\n\n".join(texts)
    print(f"Tổng ký tự sau OCR: {len(combined)}")

    # 3. Chuyển text → MP3
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    chunks = split_text(combined, max_chars=3000)
    total = len(chunks)
    print(f"Tổng số đoạn: {total}")

    output_file = output_path / f"{output_stem}.mp3"
    with open(str(output_file), 'wb') as outf:
        for i, chunk in enumerate(chunks, 1):
            if (i - 1) % 20 == 0 or i == total:
                print(f"  Đoạn {i}/{total}...")
            data = chunk_to_mp3_bytes(chunk, lang)
            outf.write(data)
            time.sleep(1.0)

    size_mb = output_file.stat().st_size / 1024 / 1024
    print(f"Đã lưu: {output_file} ({size_mb:.1f} MB)")
    return output_file


if __name__ == "__main__":
    # --multi <output_stem> <img1> <img2> ...
    if len(sys.argv) > 3 and sys.argv[1] == "--multi":
        convert_multi_images(sys.argv[3:], sys.argv[2])
    elif len(sys.argv) > 1:
        convert_to_mp3(sys.argv[1])
    else:
        convert_all_in_folder()
