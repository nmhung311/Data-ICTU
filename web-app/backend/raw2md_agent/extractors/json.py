"""
JSON text extraction for Raw2MD Agent.

Recursively extracts text fields from JSON files and flattens nested structures.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from .base import BaseExtractor, ExtractionError, CorruptedFileError

logger = logging.getLogger(__name__)


class JSONExtractor(BaseExtractor):
    """
    JSON text extractor with recursive flattening.
    
    Features:
    - Recursive text field extraction
    - Handle nested objects and arrays
    - Preserve structure information
    - Flatten complex JSON structures
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize JSON extractor.
        
        Args:
            path: Path to JSON file
            config: Optional configuration dictionary
        """
        super().__init__(path, config)
        
        # JSON configuration
        self.max_depth = config.get('max_depth', 10) if config else 10
        self.include_keys = config.get('include_keys', True) if config else True
        self.flatten_arrays = config.get('flatten_arrays', True) if config else True
    
    def extract(self) -> str:
        """
        Extract text from JSON file.
        
        Returns:
            Extracted text content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If JSON is corrupted
        """
        try:
            # Read JSON content
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                json_content = f.read()
            
            if not json_content.strip():
                raise ExtractionError("JSON file is empty", str(self.path))
            
            # Parse JSON
            try:
                data = json.loads(json_content)
            except json.JSONDecodeError as e:
                raise CorruptedFileError(f"JSON parsing error: {e}", str(self.path), e)
            
            # Extract text recursively
            extracted_text = self._extract_text_recursive(data, "")
            
            if not extracted_text.strip():
                raise ExtractionError("No text content found in JSON", str(self.path))
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from JSON")
            return extracted_text
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract text from JSON: {e}", str(self.path), e)
    
    def _extract_text_recursive(self, data: Any, path: str, depth: int = 0) -> str:
        """
        Recursively extract text from JSON data.
        
        Args:
            data: JSON data to extract from
            path: Current path in the JSON structure
            depth: Current recursion depth
            
        Returns:
            Extracted text content
        """
        if depth > self.max_depth:
            return ""
        
        extracted_lines = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, (str, int, float, bool)):
                    # Leaf value
                    if self.include_keys:
                        extracted_lines.append(f"**{current_path}:** {value}")
                    else:
                        extracted_lines.append(str(value))
                else:
                    # Nested structure
                    nested_text = self._extract_text_recursive(value, current_path, depth + 1)
                    if nested_text:
                        extracted_lines.append(nested_text)
        
        elif isinstance(data, list):
            if self.flatten_arrays:
                for i, item in enumerate(data):
                    current_path = f"{path}[{i}]" if path else f"[{i}]"
                    nested_text = self._extract_text_recursive(item, current_path, depth + 1)
                    if nested_text:
                        extracted_lines.append(nested_text)
            else:
                # Treat array as single block
                array_items = []
                for item in data:
                    if isinstance(item, (str, int, float, bool)):
                        array_items.append(str(item))
                    else:
                        nested_text = self._extract_text_recursive(item, "", depth + 1)
                        if nested_text:
                            array_items.append(nested_text)
                
                if array_items:
                    if self.include_keys and path:
                        extracted_lines.append(f"**{path}:**")
                    extracted_lines.extend(array_items)
        
        elif isinstance(data, (str, int, float, bool)):
            # Simple value
            if self.include_keys and path:
                extracted_lines.append(f"**{path}:** {data}")
            else:
                extracted_lines.append(str(data))
        
        return '\n'.join(extracted_lines)
    
    def get_json_structure(self) -> Dict[str, Any]:
        """
        Get the structure of the JSON file.
        
        Returns:
            Dictionary describing the JSON structure
        """
        try:
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                json_content = f.read()
            
            data = json.loads(json_content)
            
            structure = {
                'type': type(data).__name__,
                'size': len(str(data)),
                'keys': [],
                'depth': 0
            }
            
            if isinstance(data, dict):
                structure['keys'] = list(data.keys())
                structure['depth'] = self._calculate_depth(data)
            elif isinstance(data, list):
                structure['length'] = len(data)
                structure['depth'] = self._calculate_depth(data)
            
            return structure
            
        except Exception as e:
            logger.warning(f"Error getting JSON structure: {e}")
            return {}
    
    def _calculate_depth(self, data: Any, current_depth: int = 0) -> int:
        """
        Calculate the maximum depth of nested structures.
        
        Args:
            data: Data to analyze
            current_depth: Current depth level
            
        Returns:
            Maximum depth
        """
        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(self._calculate_depth(value, current_depth + 1) for value in data.values())
        elif isinstance(data, list):
            if not data:
                return current_depth
            return max(self._calculate_depth(item, current_depth + 1) for item in data)
        else:
            return current_depth
    
    def extract_by_path(self, json_path: str) -> Any:
        """
        Extract specific value by JSON path.
        
        Args:
            json_path: Dot-separated path (e.g., "user.name")
            
        Returns:
            Value at the specified path
        """
        try:
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                json_content = f.read()
            
            data = json.loads(json_content)
            
            # Navigate to the path
            current = data
            for key in json_path.split('.'):
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            return current
            
        except Exception as e:
            logger.warning(f"Error extracting by path {json_path}: {e}")
            return None
    
    def get_all_keys(self) -> List[str]:
        """
        Get all keys from the JSON file.
        
        Returns:
            List of all keys (including nested paths)
        """
        try:
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                json_content = f.read()
            
            data = json.loads(json_content)
            return self._get_keys_recursive(data, "")
            
        except Exception as e:
            logger.warning(f"Error getting all keys: {e}")
            return []
    
    def _get_keys_recursive(self, data: Any, path: str) -> List[str]:
        """
        Recursively get all keys from JSON data.
        
        Args:
            data: JSON data
            path: Current path
            
        Returns:
            List of all keys
        """
        keys = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                keys.append(current_path)
                
                if isinstance(value, (dict, list)):
                    keys.extend(self._get_keys_recursive(value, current_path))
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                
                if isinstance(item, (dict, list)):
                    keys.extend(self._get_keys_recursive(item, current_path))
        
        return keys
