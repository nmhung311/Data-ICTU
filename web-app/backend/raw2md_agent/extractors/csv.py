"""
CSV to Markdown conversion for Raw2MD Agent.

Uses pandas to read CSV files and convert them to Markdown tables.
"""

import logging
from typing import Optional, Dict, Any

from .base import BaseExtractor, ExtractionError, CorruptedFileError

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available. CSV extraction will not work.")


class CSVExtractor(BaseExtractor):
    """
    CSV to Markdown converter using pandas.
    
    Features:
    - Automatic separator detection
    - Convert to Markdown tables
    - Handle various CSV formats
    - Preserve data types
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CSV extractor.
        
        Args:
            path: Path to CSV file
            config: Optional configuration dictionary
        """
        super().__init__(path, config)
        
        if not PANDAS_AVAILABLE:
            raise ExtractionError("pandas library not available", str(self.path))
        
        # CSV configuration
        self.separator = config.get('separator', None) if config else None
        self.encoding = config.get('encoding', 'utf-8') if config else 'utf-8'
        self.max_rows = config.get('max_rows', 1000) if config else 1000
    
    def extract(self) -> str:
        """
        Extract and convert CSV to Markdown.
        
        Returns:
            Converted Markdown table content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If CSV is corrupted
        """
        try:
            if not PANDAS_AVAILABLE:
                raise ExtractionError("pandas library not available", str(self.path))
                
            # Detect separator if not specified
            separator = self.separator or self._detect_separator()
            
            # Read CSV file
            df = pd.read_csv(
                self.path,
                sep=separator,
                encoding=self.encoding,
                nrows=self.max_rows,
                dtype=str  # Read all as strings to preserve formatting
            )
            
            if df.empty:
                raise ExtractionError("CSV file is empty", str(self.path))
            
            # Convert to Markdown
            markdown_content = self._dataframe_to_markdown(df)
            
            # Add metadata
            metadata = self._generate_metadata(df)
            full_content = f"{metadata}\n\n{markdown_content}"
            
            logger.info(f"Successfully converted CSV to Markdown with {len(df)} rows and {len(df.columns)} columns")
            return full_content
            
        except Exception as e:
            if "empty" in str(e).lower():
                raise ExtractionError("CSV file is empty", str(self.path))
            elif "parse" in str(e).lower() or "decode" in str(e).lower():
                raise CorruptedFileError(f"CSV parsing error: {e}", str(self.path), e)
            else:
                raise ExtractionError(f"Failed to extract text from CSV: {e}", str(self.path), e)
    
    def _detect_separator(self) -> str:
        """
        Detect CSV separator automatically.
        
        Returns:
            Detected separator character
        """
        try:
            # Read first few lines to detect separator
            with open(self.path, 'r', encoding=self.encoding, errors='replace') as f:
                sample = f.read(1024)
            
            # Count occurrences of common separators
            separators = [',', ';', '\t', '|']
            separator_counts = {}
            
            for sep in separators:
                separator_counts[sep] = sample.count(sep)
            
            # Choose separator with highest count
            if separator_counts:
                detected_separator = max(separator_counts.keys(), key=lambda k: separator_counts[k])
            else:
                detected_separator = ','
            
            logger.debug(f"Detected CSV separator: '{detected_separator}'")
            return detected_separator
            
        except Exception as e:
            logger.warning(f"Error detecting separator: {e}, using comma")
            return ','
    
    def _dataframe_to_markdown(self, df) -> str:
        """
        Convert pandas DataFrame to Markdown table.
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Markdown table string
        """
        try:
            # Use pandas built-in to_markdown method
            markdown_table = df.to_markdown(index=False, tablefmt='pipe')
            
            # Clean up the output
            lines = markdown_table.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Remove excessive whitespace
                line = line.strip()
                if line:
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.warning(f"Error converting to Markdown: {e}")
            # Fallback: simple table format
            return self._simple_table_format(df)
    
    def _simple_table_format(self, df) -> str:
        """
        Simple table formatting fallback.
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Simple formatted table string
        """
        lines = []
        
        # Header
        header = ' | '.join(df.columns)
        lines.append(header)
        
        # Separator
        separator = ' | '.join(['---'] * len(df.columns))
        lines.append(separator)
        
        # Data rows
        for _, row in df.iterrows():
            row_data = ' | '.join(str(cell) for cell in row.values)
            lines.append(row_data)
        
        return '\n'.join(lines)
    
    def _generate_metadata(self, df) -> str:
        """
        Generate metadata for the CSV content.
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Metadata string
        """
        metadata_lines = [
            f"**File Type:** CSV",
            f"**Rows:** {len(df)}",
            f"**Columns:** {len(df.columns)}",
            f"**Columns:** {', '.join(df.columns)}",
        ]
        
        return '\n'.join(metadata_lines)
    
    def get_row_count(self) -> int:
        """
        Get the number of rows in the CSV file.
        
        Returns:
            Number of rows
        """
        if not PANDAS_AVAILABLE:
            return 0
            
        try:
            separator = self.separator or self._detect_separator()
            df = pd.read_csv(self.path, sep=separator, encoding=self.encoding)
            return len(df)
        except Exception as e:
            logger.warning(f"Error getting row count: {e}")
            return 0
    
    def get_column_count(self) -> int:
        """
        Get the number of columns in the CSV file.
        
        Returns:
            Number of columns
        """
        if not PANDAS_AVAILABLE:
            return 0
            
        try:
            separator = self.separator or self._detect_separator()
            df = pd.read_csv(self.path, sep=separator, encoding=self.encoding, nrows=1)
            return len(df.columns)
        except Exception as e:
            logger.warning(f"Error getting column count: {e}")
            return 0
    
    def get_column_names(self) -> list:
        """
        Get the column names from the CSV file.
        
        Returns:
            List of column names
        """
        if not PANDAS_AVAILABLE:
            return []
            
        try:
            separator = self.separator or self._detect_separator()
            df = pd.read_csv(self.path, sep=separator, encoding=self.encoding, nrows=1)
            return df.columns.tolist()
        except Exception as e:
            logger.warning(f"Error getting column names: {e}")
            return []
