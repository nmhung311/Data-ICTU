"""
Raw2MD Agent - Production Document Processing Pipeline

A scalable system for converting any document format to clean Markdown
with Vietnamese administrative metadata extraction.
"""

# Fix annotationlib import error for Python 3.11+
def fix_annotationlib_import():
    """Fix annotationlib import issues for Python 3.11+"""
    try:
        # Try to import annotationlib
        import annotationlib
        # Check if the problematic function exists
        if hasattr(annotationlib, 'get_annotate_from_class_namespace'):
            # If it exists, we're good
            return True
        else:
            # If it doesn't exist, add a proper function to prevent errors
            def dummy_get_annotate_from_class_namespace(obj):
                # Return empty dict instead of None to avoid Pydantic issues
                return getattr(obj, '__annotations__', {})
            annotationlib.get_annotate_from_class_namespace = dummy_get_annotate_from_class_namespace
            print("Applied annotationlib monkey patch")
            return True
    except ImportError:
        # annotationlib not available, which is fine
        return True
    except Exception as e:
        print(f"annotationlib error: {e}")
        return False

# Apply the fix immediately
fix_annotationlib_import()

__version__ = "1.0.0"
__author__ = "Raw2MD Agent Team"
__email__ = "team@raw2md.dev"

from .config_dataclasses import Config, get_config
from .detector import detect_type
from .extractors import get_extractor
from .cleaner import clean_text
from .metadata_agent import analyze_document
from .markdown_builder import build_metadata_block, compose_markdown
from .validator import validate
from .exporter import export_to_md

__all__ = [
    "Config",
    "get_config",
    "detect_type",
    "get_extractor",
    "clean_text",
    "analyze_document",
    "build_metadata_block",
    "compose_markdown",
    "validate",
    "export_to_md",
]
