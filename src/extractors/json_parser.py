"""
JSON file parsing for field extraction.
"""

import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class JSONParser:
    """Parse JSON files containing field definitions."""

    def __init__(
        self,
        flatten_nested: bool = True,
        separator: str = ".",
        ignore_keys: Optional[List[str]] = None
    ):
        """
        Initialize JSON parser.

        Args:
            flatten_nested: Whether to flatten nested dictionaries
            separator: Separator for nested keys when flattening
            ignore_keys: List of keys to ignore during parsing
        """
        self.flatten_nested = flatten_nested
        self.separator = separator
        self.ignore_keys = ignore_keys or []

    def parse(self, json_path: str) -> Dict[str, Any]:
        """
        Parse JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            Dictionary with parsed data
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if self.flatten_nested and isinstance(data, dict):
                data = self._flatten_dict(data)

            return data

        except FileNotFoundError:
            logger.error(f"JSON file not found: {json_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON file {json_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON {json_path}: {e}")
            raise

    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = "",
        sep: str = None
    ) -> Dict[str, Any]:
        """
        Flatten nested dictionary.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key for recursion
            sep: Separator for keys

        Returns:
            Flattened dictionary
        """
        if sep is None:
            sep = self.separator

        items = []

        for k, v in d.items():
            # Skip ignored keys
            if k in self.ignore_keys:
                continue

            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Handle lists
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(
                            self._flatten_dict(item, f"{new_key}[{i}]", sep=sep).items()
                        )
                    else:
                        items.append((f"{new_key}[{i}]", item))
            else:
                items.append((new_key, v))

        return dict(items)

    def extract_fields(
        self,
        json_path: str,
        field_filter: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Extract fields from JSON, converting all values to strings.

        Args:
            json_path: Path to JSON file
            field_filter: Optional list of field names to extract

        Returns:
            Dictionary of field_name -> value_as_string
        """
        data = self.parse(json_path)

        # Convert all values to strings
        fields = {}
        for key, value in data.items():
            if field_filter is None or key in field_filter:
                # Convert value to string
                if value is None:
                    fields[key] = ""
                elif isinstance(value, (list, dict)):
                    fields[key] = json.dumps(value, ensure_ascii=False)
                else:
                    fields[key] = str(value)

        return fields

    def extract_text_values(self, json_path: str) -> List[str]:
        """
        Extract all text values from JSON (for searching).

        Args:
            json_path: Path to JSON file

        Returns:
            List of unique text values
        """
        data = self.parse(json_path)

        text_values = set()

        for value in data.values():
            if isinstance(value, str) and value.strip():
                text_values.add(value)
            elif isinstance(value, (int, float)):
                text_values.add(str(value))

        return list(text_values)

    def get_field_metadata(
        self,
        json_path: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata about fields in JSON.

        Args:
            json_path: Path to JSON file

        Returns:
            Dictionary mapping field names to metadata
        """
        data = self.parse(json_path)

        metadata = {}

        for key, value in data.items():
            value_type = type(value).__name__
            value_length = len(str(value)) if value else 0

            metadata[key] = {
                'type': value_type,
                'length': value_length,
                'is_numeric': isinstance(value, (int, float)),
                'is_text': isinstance(value, str),
                'is_empty': value is None or (isinstance(value, str) and not value.strip())
            }

        return metadata

    @staticmethod
    def validate_json(json_path: str) -> bool:
        """
        Validate if file is valid JSON.

        Args:
            json_path: Path to JSON file

        Returns:
            True if valid, False otherwise
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    @staticmethod
    def find_matching_json(pdf_path: str) -> Optional[str]:
        """
        Find JSON file matching PDF file name.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Path to matching JSON file or None
        """
        pdf_file = Path(pdf_path)
        json_file = pdf_file.with_suffix('.json')

        if json_file.exists():
            return str(json_file)

        return None

    def create_field_value_pairs(
        self,
        json_path: str,
        include_keys: bool = True
    ) -> List[Dict[str, str]]:
        """
        Create list of field-value pairs for matching.

        Args:
            json_path: Path to JSON file
            include_keys: Whether to include field names in output

        Returns:
            List of dictionaries with field info
        """
        fields = self.extract_fields(json_path)

        pairs = []

        for field_name, field_value in fields.items():
            pair = {
                'field_name': field_name,
                'field_value': field_value,
                'search_text': field_value
            }

            if include_keys:
                # Also search for the field name itself
                pair['field_name_text'] = field_name.split(self.separator)[-1]

            pairs.append(pair)

        return pairs
