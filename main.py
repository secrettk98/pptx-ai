"""
Main entry point for the PowerPoint AI redesign application.
"""

from pathlib import Path
from dotenv import load_dotenv
import logging

from processors.json_to_slide import build_slide_from_json


def setup_logging() -> None:
    """
    Configure logging with INFO level and specific format.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def main() -> None:
    """
    Main application function that orchestrates the PowerPoint presentation creation.
    """
    setup_logging()
    load_dotenv()
    logging.info("Application started")

    json_path = Path("assets") / "test_slide.json"
    output_path = Path("storage") / "output.pptx"

    build_slide_from_json(json_path, output_path)

    logging.info(f"Presentation saved to {output_path}")


if __name__ == "__main__":
    main()
