"""
Module for building PowerPoint presentations using python-pptx.
"""

from pathlib import Path
from pptx import Presentation
import logging


logger = logging.getLogger(__name__)


def create_empty_presentation(output_path: str) -> None:
    """
    Create an empty PowerPoint presentation and save it to the specified path.
    
    This function creates a new presentation based on the default template
    and saves it to the given output path.
    
    Args:
        output_path (str): The file path where the presentation will be saved.
                           Should end with .pptx extension.
    
    Returns:
        None
    
    Raises:
        Exception: If there's an error during presentation creation or saving.
    
    Example:
        >>> create_empty_presentation("my_presentation.pptx")
        # Creates an empty presentation and saves it as my_presentation.pptx
    """
    try:

        presentation = Presentation()
        

        output_file = Path(output_path)
        

        output_file.parent.mkdir(parents=True, exist_ok=True)
        

        presentation.save(output_file)
        
        logger.info(f"Empty presentation created successfully at {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to create empty presentation at {output_path}: {str(e)}")
        raise