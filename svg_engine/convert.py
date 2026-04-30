"""Обертка для конвертации массива SVG файлов в формат PPTX."""

import sys
from pathlib import Path

from core.logger import get_logger
from .pptx_builder import create_pptx_with_native_svg

log = get_logger(__name__)


def svg_to_pptx(svg_paths: list[Path], output_path: str | Path) -> Path:
    """Конвертирует список переданных SVG-файлов в PPTX-презентацию."""
    try:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"Converting {len(svg_paths)} SVG files to PPTX...")
        
        success = create_pptx_with_native_svg(
            svg_files=svg_paths,
            output_path=out_path,
            use_native_shapes=True,
            verbose=True,
        )
        
        if success:
            log.info(f"PPTX saved: {out_path}")
        else:
            log.warning("Some slides failed during conversion")
            
        return out_path
    except Exception as e:
        log.error(f"Ошибка конвертации SVG в PPTX: {e}")
        raise


if __name__ == "__main__":
    try:
        svg_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("temp/svg")
        svg_files = sorted(svg_dir.glob("*.svg"))
        
        if not svg_files:
            print(f"No SVG files found in {svg_dir}")
            sys.exit(1)
            
        print(f"Found {len(svg_files)} SVG files")
        result = svg_to_pptx(svg_files, "output/test_convert.pptx")
        print(f"Result: {result}")
    except Exception as e:
        log.error(f"Критическая ошибка выполнения: {e}")
        sys.exit(1)