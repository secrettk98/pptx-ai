"""Точка входа приложения PPTX-AI для запуска редизайна презентаций из командной строки."""

import argparse
from core.orchestrator import run_redesign


def main() -> None:
    """Парсит аргументы командной строки и запускает главный пайплайн оркестратора."""
    parser = argparse.ArgumentParser(description="PPTX-AI: AI-powered presentation redesign")
    
    parser.add_argument(
        "input",
        type=str,
        help="Path to input PPTX file"
    )
    
    parser.add_argument(
        "--accent",
        type=str,
        default="#0066CC",
        help="Accent color hex"
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        default="pitch",
        choices=["pitch", "report", "training", "commercial"],
        help="Presentation mode"
    )
    
    args = parser.parse_args()
    
    result = run_redesign(
        input_pptx=args.input,
        accent_color=args.accent,
        mode=args.mode
    )
    
    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()