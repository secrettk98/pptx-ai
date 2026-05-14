"""Модуль для конвертации слайдов PPTX в изображения JPG через LibreOffice."""

import subprocess
from pathlib import Path
from pdf2image import convert_from_path

import logging
from core.config import TEMP_DIR

log = logging.getLogger(__name__)

LIBREOFFICE_PATH: str = r"C:\Program Files\LibreOffice\program\soffice.exe"


def render_slides(pptx_path: str | Path, output_dir: str | Path = None) -> list[Path]:
    """Конвертирует презентацию в PDF, а затем постранично в JPG изображения."""
    pptx_path = Path(pptx_path)
    output_dir_path = Path(output_dir) if output_dir else TEMP_DIR / "slides"
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    log.info(f"Converting {pptx_path.name} to JPG...")

    # Шаг A: PPTX -> PDF через LibreOffice headless
    pdf_dir = TEMP_DIR / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        LIBREOFFICE_PATH, 
        "--headless", 
        "--convert-to", "pdf", 
        "--outdir", str(pdf_dir), 
        str(pptx_path)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as e:
        log.error(f"Таймаут конвертации LibreOffice для {pptx_path.name}: {e}")
        raise RuntimeError(f"Таймаут LibreOffice: {e}") from e
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode("utf-8", errors="ignore")
        log.error(f"Ошибка LibreOffice: {error_msg}")
        raise RuntimeError(f"Сбой LibreOffice при конвертации: {error_msg}") from e

    pdf_path = pdf_dir / (pptx_path.stem + ".pdf")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not created: {pdf_path}")

    # Шаг B: PDF -> JPG через pdf2image
    try:
        images = convert_from_path(str(pdf_path), dpi=200)
    except Exception as e:
        log.error(f"Не удалось извлечь изображения из PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"Ошибка pdf2image: {e}") from e

    result: list[Path] = []
    for idx, img in enumerate(images):
        jpg_path = output_dir_path / f"slide_{idx}.jpg"
        try:
            img.save(str(jpg_path), "JPEG", quality=90)
            result.append(jpg_path)
            log.info(f"  Slide {idx} -> {jpg_path.name}")
        except Exception as e:
            log.error(f"Ошибка сохранения изображения {jpg_path.name}: {e}")
            raise RuntimeError(f"Не удалось сохранить JPG: {e}") from e

    log.info(f"Rendered {len(result)} slides")
    return result


if __name__ == "__main__":
    import sys
    
    path = sys.argv[1] if len(sys.argv) > 1 else "projects/test_map/test_maps.pptx"
    
    try:
        slides = render_slides(path)
        print(f"Done: {len(slides)} images")
        for s in slides:
            print(f"  {s}")
    except Exception as err:
        print(f"Error during execution: {err}")