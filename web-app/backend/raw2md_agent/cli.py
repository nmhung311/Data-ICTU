"""
Command-line interface for Raw2MD Agent.

Provides simple CLI for single-file processing with various options.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from .detector import detect_type, is_supported_format
from .extractors import get_extractor
from .cleaner import clean_text
from .metadata_agent import analyze_document
from .markdown_builder import build_metadata_block, compose_markdown
from .validator import validate
from .exporter import export_to_md

logger = logging.getLogger(__name__)


def setup_logging(level: str = 'INFO', format_type: str = 'text') -> None:
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if format_type.lower() == 'json':
        import json
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                }
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_entry)
        
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)


def process_single_file(input_path: str, output_dir: str = './output', 
                       ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                       lang: str = 'vi', config: Optional[Dict[str, Any]] = None) -> Path:
    """
    Process a single file and convert to Markdown.
    
    Args:
        input_path: Path to input file
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode (regex/llm/hybrid)
        lang: Language code
        config: Optional configuration dictionary
        
    Returns:
        Path to exported Markdown file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If file type is not supported
        Exception: If processing fails
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    logger.info(f"Processing file: {input_file}")
    
    # Detect file type
    file_type = detect_type(str(input_file))
    logger.info(f"Detected file type: {file_type}")
    
    if not is_supported_format(file_type):
        logger.warning(f"Unsupported file type: {file_type}")
        file_type = 'unknown'  # Use fallback extractor
    
    # Prepare extractor configuration
    extractor_config = {
        'use_gpu': ocr_enabled,
        'lang': lang,
        'confidence_threshold': 0.6,
    }
    
    # Extract text
    logger.info("Extracting text content...")
    extractor = get_extractor(file_type, str(input_file), extractor_config)
    raw_text = extractor.extract()
    
    if not raw_text or not raw_text.strip():
        raise ValueError("No text content extracted from file")
    
    logger.info(f"Extracted {len(raw_text)} characters")
    
    # Clean text
    logger.info("Cleaning text content...")
    cleaned_text = clean_text(raw_text)
    logger.info(f"Cleaned text: {len(cleaned_text)} characters")
    
    # Extract metadata
    logger.info(f"Extracting metadata using {agent_mode} mode...")
    
    # Prepare metadata agent configuration
    metadata_config = config or {}
    if 'api_key' in metadata_config:
        metadata_config['llm_enabled'] = True
    
    metadata = analyze_document(cleaned_text, metadata_config, agent_mode)
    logger.info(f"Extracted metadata: {metadata}")
    
    # Build markdown
    logger.info("Building markdown document...")
    metadata_block = build_metadata_block(metadata)
    markdown_content = compose_markdown(metadata_block, cleaned_text, metadata)
    
    # Validate output
    logger.info("Validating output...")
    is_valid = validate(markdown_content, metadata)
    if not is_valid:
        logger.warning("Output validation failed, but continuing...")
    
    # Export to file
    logger.info(f"Exporting to directory: {output_dir}")
    output_path = export_to_md(markdown_content, metadata, output_dir)
    
    logger.info(f"Successfully processed file: {output_path}")
    return output_path


def process_directory(input_dir: str, output_dir: str = './output',
                     ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                     lang: str = 'vi', config: Optional[Dict[str, Any]] = None) -> list:
    """
    Process all supported files in a directory.
    
    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config: Optional configuration dictionary
        
    Returns:
        List of exported file paths
    """
    input_path = Path(input_dir)
    
    if not input_path.exists() or not input_path.is_dir():
        raise ValueError(f"Input directory not found: {input_dir}")
    
    # Find all supported files
    supported_extensions = {'.pdf', '.docx', '.html', '.htm', '.txt', '.csv', 
                           '.xml', '.json', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'}
    
    files_to_process = []
    for ext in supported_extensions:
        files_to_process.extend(input_path.glob(f'*{ext}'))
        files_to_process.extend(input_path.glob(f'*{ext.upper()}'))
    
    if not files_to_process:
        logger.warning(f"No supported files found in directory: {input_dir}")
        return []
    
    logger.info(f"Found {len(files_to_process)} files to process")
    
    # Process each file
    results = []
    for i, file_path in enumerate(files_to_process, 1):
        try:
            logger.info(f"Processing file {i}/{len(files_to_process)}: {file_path.name}")
            output_path = process_single_file(
                str(file_path), output_dir, ocr_enabled, agent_mode, lang, config
            )
            results.append(output_path)
            
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            results.append(None)
    
    successful = len([r for r in results if r is not None])
    logger.info(f"Successfully processed {successful}/{len(files_to_process)} files")
    
    return results


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Raw2MD Agent - Convert any document to clean Markdown with Vietnamese metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single PDF file
  python -m raw2md_agent --input document.pdf --output ./output

  # Process all files in a directory with OCR enabled
  python -m raw2md_agent --input ./documents --output ./output --ocr true

  # Use LLM mode for metadata extraction
  python -m raw2md_agent --input document.pdf --agent llm --api-key YOUR_API_KEY

  # Process with custom configuration
  python -m raw2md_agent --input document.pdf --config config.json
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to input file or directory'
    )
    
    # Optional arguments
    parser.add_argument(
        '--output', '-o',
        default='./output',
        help='Output directory (default: ./output)'
    )
    
    parser.add_argument(
        '--ocr',
        type=lambda x: x.lower() in ['true', '1', 'yes', 'on'],
        default=True,
        help='Enable OCR processing (default: true)'
    )
    
    parser.add_argument(
        '--agent',
        choices=['regex', 'llm', 'hybrid'],
        default='hybrid',
        help='Metadata extraction mode (default: hybrid)'
    )
    
    parser.add_argument(
        '--lang',
        default='vi',
        help='Language code for OCR (default: vi)'
    )
    
    parser.add_argument(
        '--api-key',
        help='Google API key for Gemini LLM (required for LLM mode)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration file (JSON)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-format',
        choices=['text', 'json'],
        default='text',
        help='Log format (default: text)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    import json
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file {config_path}: {e}")
        return {}


def main() -> int:
    """Main CLI entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else args.log_level
    setup_logging(log_level, args.log_format)
    
    try:
        # Load configuration
        config = {}
        if args.config:
            config = load_config_file(args.config)
        
        # Add API key to config if provided
        if args.api_key:
            config['api_key'] = args.api_key
            config['llm_enabled'] = True
        
        # Determine if input is file or directory
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Process single file
            logger.info("Processing single file")
            output_path = process_single_file(
                args.input, args.output, args.ocr, args.agent, args.lang, config
            )
            print(f"[OK] Successfully processed: {output_path}")
            
        elif input_path.is_dir():
            # Process directory
            logger.info("Processing directory")
            results = process_directory(
                args.input, args.output, args.ocr, args.agent, args.lang, config
            )
            successful = len([r for r in results if r is not None])
            print(f"[OK] Successfully processed {successful} files")
            
        else:
            logger.error(f"Input path not found: {args.input}")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 130
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
