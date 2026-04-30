"""svg_engine — SVG to PPTX conversion (based on PPT Master, MIT license)."""

from .drawingml_converter import convert_svg_to_slide_shapes
from .pptx_builder import create_pptx_with_native_svg