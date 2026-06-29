#!/usr/bin/env python3
"""
Tạo + upload HF Space (Docker) cho OCR service. Cần: export HF_TOKEN=hf_...

Dựng staging trong /tmp với layout Space:
  Dockerfile, README.md, requirements.txt, ocr/<package .py + index.html>
rồi create_repo + upload_folder.

Chạy:
  cd ocr/hf-space
  export HF_TOKEN=hf_xxx
  python3 deploy_space.py
"""
import os
import sys
import shutil
import tempfile
from pathlib import Path

HF_DIR = Path(__file__).resolve().parent      # ocr/hf-space
OCR_DIR = HF_DIR.parent                        # ocr/
PKG_FILES = ["__init__.py", "base.py", "paddle_engine.py", "groq_engine.py",
             "parser.py", "extractor.py", "api.py", "index.html",
             "obituary.py", "address_parser.py", "map_service.py",
             "speech_generator.py", "tts_service.py"]


def main():
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        sys.exit("Thiếu HF_TOKEN (huggingface.co/settings/tokens).")

    from huggingface_hub import HfApi, whoami
    api = HfApi(token=token)
    user = whoami(token=token)["name"]
    space_name = os.environ.get("SPACE_NAME", "ocr-numbers")
    repo_id = f"{user}/{space_name}"

    stage = Path(tempfile.mkdtemp(prefix="ocr-space-"))
    (stage / "ocr").mkdir()
    shutil.copy(HF_DIR / "Dockerfile", stage / "Dockerfile")
    shutil.copy(HF_DIR / "README.md", stage / "README.md")
    # Dùng requirements NHẸ của hf-space (biến thể groq), không phải bản paddle đầy đủ.
    shutil.copy(HF_DIR / "requirements.txt", stage / "requirements.txt")
    for f in PKG_FILES:
        shutil.copy(OCR_DIR / f, stage / "ocr" / f)

    print(f"→ tạo Space {repo_id} (docker)...")
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", exist_ok=True)

    # Cấu hình engine + key. OCR_ENGINE mặc định groq; GROQ_API_KEY lấy từ ENV (đặt làm secret).
    engine = os.getenv("OCR_ENGINE", "groq")
    api.add_space_variable(repo_id=repo_id, key="OCR_ENGINE", value=engine)
    gk = os.getenv("GROQ_API_KEY")
    if gk:
        api.add_space_secret(repo_id=repo_id, key="GROQ_API_KEY", value=gk)
        print("→ đã set secret GROQ_API_KEY")
    else:
        print("⚠ Chưa có GROQ_API_KEY trong ENV — nhớ set thủ công ở Space Settings.")
    gm = os.getenv("GROQ_VISION_MODEL")
    if gm:
        api.add_space_variable(repo_id=repo_id, key="GROQ_VISION_MODEL", value=gm)

    print("→ upload...")
    api.upload_folder(folder_path=str(stage), repo_id=repo_id, repo_type="space",
                      commit_message="ocr-numbers deploy")
    shutil.rmtree(stage, ignore_errors=True)

    print("\n================= XONG =================")
    print(f"Space:    https://huggingface.co/spaces/{repo_id}")
    print(f"Endpoint: https://{user}-{space_name}.hf.space   (GET / = demo, POST /ocr)")
    print("Space tự build (~chục phút: cài paddle + warm model). Theo dõi tab Logs.")


if __name__ == "__main__":
    main()
