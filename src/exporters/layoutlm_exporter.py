"""
Export bounding boxes in LayoutLM format (normalized 0-1000 scale).
"""

import json
from typing import List, Dict, Any, Tuple
from pathlib import Path
import logging

from ..normalizers.coord_normalizer import CoordinateNormalizer
from ..matchers.exact_matcher import Match

logger = logging.getLogger(__name__)


class LayoutLMExporter:
    """Export annotations in LayoutLM format."""

    def __init__(self, target_scale: int = 1000):
        """
        Initialize LayoutLM exporter.

        Args:
            target_scale: Target normalization scale (default 1000)
        """
        self.target_scale = target_scale
        self.coord_normalizer = CoordinateNormalizer()

    def export(
        self,
        matches: List[Match],
        field_names: List[str],
        output_path: str,
        include_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        Export matches to LayoutLM format.

        Args:
            matches: List of Match objects
            field_names: List of field names corresponding to matches
            output_path: Path to save output JSON
            include_confidence: Include confidence scores in output

        Returns:
            Dictionary in LayoutLM format
        """
        if len(matches) != len(field_names):
            raise ValueError(
                f"Number of matches ({len(matches)}) must equal "
                f"number of field names ({len(field_names)})"
            )

        # Group by page
        pages_data = {}

        for match, field_name in zip(matches, field_names):
            page_num = match.page_num

            if page_num not in pages_data:
                pages_data[page_num] = {
                    'page': page_num,
                    'width': match.metadata.get('page_width', 0),
                    'height': match.metadata.get('page_height', 0),
                    'annotations': []
                }

            # Normalize bbox
            normalized_bbox = self.coord_normalizer.normalize_to_scale(
                match.bbox,
                pages_data[page_num]['width'],
                pages_data[page_num]['height'],
                self.target_scale
            )

            annotation = {
                'text': match.text,
                'label': field_name,
                'bbox': list(normalized_bbox),  # [x0, y0, x1, y1]
                'match_type': match.match_type
            }

            if include_confidence:
                annotation['confidence'] = match.confidence

            pages_data[page_num]['annotations'].append(annotation)

        # Create output structure
        output_data = {
            'format': 'layoutlm',
            'scale': self.target_scale,
            'pages': list(pages_data.values())
        }

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported LayoutLM format to {output_path}")

        return output_data

    def export_with_tokens(
        self,
        matches: List[Match],
        field_names: List[str],
        words_data: List[Dict[str, Any]],
        output_path: str
    ) -> Dict[str, Any]:
        """
        Export in LayoutLM format with token-level annotations.

        Args:
            matches: List of Match objects
            field_names: List of field names
            words_data: Word-level data from PDF extractor
            output_path: Path to save output

        Returns:
            Dictionary in LayoutLM format with tokens
        """
        # Group by page
        pages_data = {}

        # First, create page structure with all words
        for word in words_data:
            page_num = word['page_num']

            if page_num not in pages_data:
                pages_data[page_num] = {
                    'page': page_num,
                    'width': word['page_width'],
                    'height': word['page_height'],
                    'tokens': [],
                    'labels': []
                }

            # Normalize bbox
            normalized_bbox = self.coord_normalizer.normalize_to_scale(
                word['bbox'],
                word['page_width'],
                word['page_height'],
                self.target_scale
            )

            pages_data[page_num]['tokens'].append({
                'text': word['text'],
                'bbox': list(normalized_bbox)
            })

            # Default label (O for outside)
            pages_data[page_num]['labels'].append('O')

        # Then, assign labels based on matches
        for match, field_name in zip(matches, field_names):
            page_num = match.page_num

            if page_num not in pages_data:
                continue

            # Find words that overlap with this match
            match_bbox = match.bbox

            for i, word in enumerate(words_data):
                if word['page_num'] != page_num:
                    continue

                word_bbox = word['bbox']

                # Check if word is inside match bbox (with tolerance)
                if self._bbox_contains(match_bbox, word_bbox, tolerance=2.0):
                    # Assign label (B-LABEL for first, I-LABEL for rest)
                    if pages_data[page_num]['labels'][i] == 'O':
                        pages_data[page_num]['labels'][i] = f'B-{field_name}'
                    else:
                        pages_data[page_num]['labels'][i] = f'I-{field_name}'

        # Create output structure
        output_data = {
            'format': 'layoutlm_tokens',
            'scale': self.target_scale,
            'pages': list(pages_data.values())
        }

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported LayoutLM token format to {output_path}")

        return output_data

    def _bbox_contains(
        self,
        outer_bbox: Tuple[float, float, float, float],
        inner_bbox: Tuple[float, float, float, float],
        tolerance: float = 0.0
    ) -> bool:
        """
        Check if outer bbox contains inner bbox.

        Args:
            outer_bbox: Outer bounding box
            inner_bbox: Inner bounding box
            tolerance: Tolerance in pixels

        Returns:
            True if outer contains inner
        """
        ox0, oy0, ox1, oy1 = outer_bbox
        ix0, iy0, ix1, iy1 = inner_bbox

        return (
            ox0 - tolerance <= ix0 and
            oy0 - tolerance <= iy0 and
            ox1 + tolerance >= ix1 and
            oy1 + tolerance >= iy1
        )

    def create_label_map(
        self,
        field_names: List[str],
        output_path: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Create label-to-id mapping for training.

        Args:
            field_names: List of unique field names
            output_path: Optional path to save label map

        Returns:
            Dictionary mapping label names to IDs
        """
        label_map = {'O': 0}
        current_id = 1

        for field_name in sorted(set(field_names)):
            label_map[f'B-{field_name}'] = current_id
            current_id += 1
            label_map[f'I-{field_name}'] = current_id
            current_id += 1

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(label_map, f, indent=2)

            logger.info(f"Saved label map to {output_path}")

        return label_map
