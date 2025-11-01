"""
Raw2MD Agent CLI Entry Point

Usage:
    python -m raw2md_agent --input path/to/file.pdf --output ./output
"""

from .cli import main

if __name__ == "__main__":
    main()
