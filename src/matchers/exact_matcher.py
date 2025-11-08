"""
Exact text matching for finding bounding boxes.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging

from ..normalizers.text_normalizer import TextNormalizer, DEFAULT_NORMALIZER
from ..normalizers.coord_normalizer import CoordinateNormalizer

logger = logging.getLogger(__name__)


@dataclass
class Match:
    """Represents a matched text with bounding box."""
    text: str
    bbox: Tuple[float, float, float, float]
    page_num: int
    confidence: float
    match_type: str
    metadata: Dict[str, Any]


class ExactMatcher:
    """Exact text matching with normalization."""

    def __init__(
        self,
        normalizer: Optional[TextNormalizer] = None,
        case_sensitive: bool = False
    ):
        """
        Initialize exact matcher.

        Args:
            normalizer: Text normalizer instance
            case_sensitive: Whether matching should be case-sensitive
        """
        self.normalizer = normalizer or DEFAULT_NORMALIZER
        self.case_sensitive = case_sensitive

    def find_matches(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        context_window: int = 5
    ) -> List[Match]:
        """
        Find exact matches of search text in words data.

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries from PDF extractor
            context_window: Number of words to consider for matching

        Returns:
            List of Match objects
        """
        matches = []

        # Normalize search text
        search_normalized = self.normalizer.normalize(search_text)
        search_tokens = search_normalized.split()

        if not search_tokens:
            return matches

        # Create sliding windows over words
        for i in range(len(words_data)):
            # Try to match starting from this word
            match = self._try_match_at_position(
                i,
                search_tokens,
                words_data,
                search_text
            )

            if match:
                matches.append(match)

        return matches

    def _try_match_at_position(
        self,
        start_idx: int,
        search_tokens: List[str],
        words_data: List[Dict[str, Any]],
        original_search_text: str
    ) -> Optional[Match]:
        """
        Try to match search tokens starting at a specific position.

        Args:
            start_idx: Starting index in words_data
            search_tokens: Tokenized search text
            words_data: List of word dictionaries
            original_search_text: Original search text (unnormalized)

        Returns:
            Match object if found, None otherwise
        """
        if start_idx + len(search_tokens) > len(words_data):
            return None

        # Collect candidate words
        candidate_words = []
        matched_indices = []

        token_idx = 0
        word_idx = start_idx

        while token_idx < len(search_tokens) and word_idx < len(words_data):
            word_data = words_data[word_idx]
            word_text = word_data['text']
            word_normalized = self.normalizer.normalize(word_text)

            # Check if this word matches the current search token
            if word_normalized == search_tokens[token_idx]:
                candidate_words.append(word_data)
                matched_indices.append(word_idx)
                token_idx += 1
                word_idx += 1
            else:
                # Check if current word is empty or whitespace
                if not word_normalized:
                    word_idx += 1
                    continue
                else:
                    # No match
                    return None

        # Check if we matched all tokens
        if token_idx == len(search_tokens):
            # Create bounding box from matched words
            bboxes = [w['bbox'] for w in candidate_words]
            merged_bbox = CoordinateNormalizer.merge_bboxes(bboxes)

            # Check if all words are on the same page
            pages = set(w['page_num'] for w in candidate_words)
            if len(pages) > 1:
                logger.warning(f"Match spans multiple pages: {pages}")
                return None

            page_num = candidate_words[0]['page_num']

            # Create match
            match = Match(
                text=original_search_text,
                bbox=merged_bbox,
                page_num=page_num,
                confidence=1.0,
                match_type="exact",
                metadata={
                    'word_count': len(candidate_words),
                    'matched_indices': matched_indices,
                    'page_width': candidate_words[0]['page_width'],
                    'page_height': candidate_words[0]['page_height']
                }
            )

            return match

        return None

    def find_all_occurrences(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]]
    ) -> List[Match]:
        """
        Find all occurrences of search text (handles duplicates).

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries

        Returns:
            List of all matches found
        """
        matches = []
        used_indices = set()

        search_normalized = self.normalizer.normalize(search_text)
        search_tokens = search_normalized.split()

        if not search_tokens:
            return matches

        for i in range(len(words_data)):
            # Skip if this position was already used
            if i in used_indices:
                continue

            match = self._try_match_at_position(
                i,
                search_tokens,
                words_data,
                search_text
            )

            if match:
                matches.append(match)
                # Mark indices as used
                for idx in match.metadata['matched_indices']:
                    used_indices.add(idx)

        return matches

    def find_best_match(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        prefer_first: bool = True
    ) -> Optional[Match]:
        """
        Find the best match (by position or confidence).

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries
            prefer_first: Prefer the first occurrence

        Returns:
            Best match or None
        """
        matches = self.find_all_occurrences(search_text, words_data)

        if not matches:
            return None

        if prefer_first:
            return matches[0]
        else:
            # Return match with highest confidence
            return max(matches, key=lambda m: m.confidence)
