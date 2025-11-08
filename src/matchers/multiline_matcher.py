"""
Multiline text matching for handling text spanning multiple lines.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

from ..normalizers.text_normalizer import TextNormalizer, DEFAULT_NORMALIZER
from ..normalizers.coord_normalizer import CoordinateNormalizer
from .exact_matcher import Match

logger = logging.getLogger(__name__)


class MultilineMatcher:
    """Handles matching of text that may span multiple lines."""

    def __init__(
        self,
        normalizer: Optional[TextNormalizer] = None,
        line_break_chars: str = "\n\r"
    ):
        """
        Initialize multiline matcher.

        Args:
            normalizer: Text normalizer instance
            line_break_chars: Characters considered as line breaks
        """
        self.normalizer = normalizer or DEFAULT_NORMALIZER
        self.line_break_chars = line_break_chars

    def find_matches(
        self,
        search_text: str,
        pdf_extractor_result,
        use_pymupdf_search: bool = True
    ) -> List[Match]:
        """
        Find matches of text that may span multiple lines.

        Args:
            search_text: Text to search for (may contain line breaks)
            pdf_extractor_result: Result from PDFExtractor
            use_pymupdf_search: Use PyMuPDF's built-in search (recommended)

        Returns:
            List of Match objects
        """
        matches = []

        # PyMuPDF's search_for handles multiline automatically
        if use_pymupdf_search:
            # This would require the PDF path and using PDFExtractor.search_text
            logger.warning(
                "Use PDFExtractor.search_text() for multiline matching with PyMuPDF"
            )
            return matches

        # Manual multiline matching (fallback)
        # Normalize search text
        search_normalized = self.normalizer.normalize_for_matching(search_text)

        # Try different line break variations
        search_variants = self._create_search_variants(search_normalized)

        for variant in search_variants:
            # Try to find this variant
            # TODO: Implement manual multiline search
            pass

        return matches

    def _create_search_variants(self, text: str) -> List[str]:
        """
        Create variants of text with different line break patterns.

        Args:
            text: Input text

        Returns:
            List of text variants
        """
        variants = [text]

        # Remove all line breaks
        no_breaks = text.replace('\n', ' ').replace('\r', ' ')
        no_breaks = ' '.join(no_breaks.split())  # Normalize whitespace
        variants.append(no_breaks)

        # Single space between words
        single_space = ' '.join(text.split())
        if single_space not in variants:
            variants.append(single_space)

        return variants

    def match_from_pymupdf_search(
        self,
        search_results: List[Dict[str, Any]],
        original_search_text: str
    ) -> List[Match]:
        """
        Convert PyMuPDF search results to Match objects.

        Args:
            search_results: Results from PDFExtractor.search_text()
            original_search_text: Original search text

        Returns:
            List of Match objects
        """
        matches = []

        for result in search_results:
            match = Match(
                text=original_search_text,
                bbox=result['bbox'],
                page_num=result['page_num'],
                confidence=1.0,
                match_type="multiline" if '\n' in original_search_text else "exact",
                metadata={
                    'page_width': result['page_width'],
                    'page_height': result['page_height'],
                    'search_type': result.get('type', 'rect')
                }
            )
            matches.append(match)

        return matches

    def merge_adjacent_matches(
        self,
        matches: List[Match],
        max_vertical_gap: float = 5.0,
        max_horizontal_gap: float = 10.0
    ) -> List[Match]:
        """
        Merge matches that are close to each other (likely same field).

        Args:
            matches: List of matches to merge
            max_vertical_gap: Maximum vertical distance to consider adjacent
            max_horizontal_gap: Maximum horizontal distance to consider adjacent

        Returns:
            List of merged matches
        """
        if not matches:
            return []

        # Sort by page and position
        sorted_matches = sorted(
            matches,
            key=lambda m: (m.page_num, m.bbox[1], m.bbox[0])
        )

        merged = []
        current_group = [sorted_matches[0]]

        for i in range(1, len(sorted_matches)):
            current = sorted_matches[i]
            previous = sorted_matches[i - 1]

            # Check if on same page
            if current.page_num != previous.page_num:
                # Different page, finalize current group
                merged.append(self._merge_match_group(current_group))
                current_group = [current]
                continue

            # Check vertical distance
            prev_bottom = previous.bbox[3]
            curr_top = current.bbox[1]
            vertical_gap = abs(curr_top - prev_bottom)

            # Check horizontal overlap or proximity
            prev_right = previous.bbox[2]
            curr_left = current.bbox[0]
            horizontal_gap = curr_left - prev_right

            # Decide if should merge
            if (vertical_gap <= max_vertical_gap and
                horizontal_gap <= max_horizontal_gap):
                current_group.append(current)
            else:
                # Finalize current group
                merged.append(self._merge_match_group(current_group))
                current_group = [current]

        # Finalize last group
        if current_group:
            merged.append(self._merge_match_group(current_group))

        return merged

    def _merge_match_group(self, matches: List[Match]) -> Match:
        """
        Merge a group of matches into a single match.

        Args:
            matches: List of matches to merge

        Returns:
            Merged match
        """
        if len(matches) == 1:
            return matches[0]

        # Merge bounding boxes
        bboxes = [m.bbox for m in matches]
        merged_bbox = CoordinateNormalizer.merge_bboxes(bboxes)

        # Combine texts
        combined_text = ' '.join(m.text for m in matches)

        # Average confidence
        avg_confidence = sum(m.confidence for m in matches) / len(matches)

        # Use first match as template
        first_match = matches[0]

        return Match(
            text=combined_text,
            bbox=merged_bbox,
            page_num=first_match.page_num,
            confidence=avg_confidence,
            match_type="merged_multiline",
            metadata={
                'merged_count': len(matches),
                'page_width': first_match.metadata.get('page_width'),
                'page_height': first_match.metadata.get('page_height'),
                'original_matches': len(matches)
            }
        )

    def split_multiline_search(
        self,
        search_text: str
    ) -> List[str]:
        """
        Split multiline search text into individual lines.

        Args:
            search_text: Search text with line breaks

        Returns:
            List of individual lines
        """
        lines = search_text.split('\n')
        # Clean and filter empty lines
        lines = [line.strip() for line in lines if line.strip()]
        return lines

    def search_by_lines(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        merge_results: bool = True
    ) -> List[Match]:
        """
        Search for multiline text by searching each line individually.

        Args:
            search_text: Multiline search text
            words_data: List of word dictionaries
            merge_results: Whether to merge adjacent line matches

        Returns:
            List of matches (merged or individual)
        """
        from .exact_matcher import ExactMatcher

        lines = self.split_multiline_search(search_text)

        if not lines:
            return []

        matcher = ExactMatcher(normalizer=self.normalizer)
        all_matches = []

        for line in lines:
            line_matches = matcher.find_all_occurrences(line, words_data)
            all_matches.extend(line_matches)

        if merge_results and all_matches:
            all_matches = self.merge_adjacent_matches(all_matches)

        return all_matches
