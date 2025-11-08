"""
Fuzzy text matching using RapidFuzz for handling variations.
"""

from typing import List, Dict, Any, Optional, Callable
from rapidfuzz import fuzz, process
import logging

from ..normalizers.text_normalizer import TextNormalizer, FUZZY_NORMALIZER
from ..normalizers.coord_normalizer import CoordinateNormalizer
from .exact_matcher import Match

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """Fuzzy text matching with configurable strategies."""

    def __init__(
        self,
        normalizer: Optional[TextNormalizer] = None,
        threshold: float = 80.0,
        scorer: Optional[Callable] = None
    ):
        """
        Initialize fuzzy matcher.

        Args:
            normalizer: Text normalizer instance
            threshold: Minimum similarity score (0-100)
            scorer: RapidFuzz scorer function (default: fuzz.ratio)
        """
        self.normalizer = normalizer or FUZZY_NORMALIZER
        self.threshold = threshold
        self.scorer = scorer or fuzz.ratio

    def find_matches(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        max_matches: int = 10
    ) -> List[Match]:
        """
        Find fuzzy matches of search text.

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries from PDF extractor
            max_matches: Maximum number of matches to return

        Returns:
            List of Match objects sorted by confidence
        """
        # Normalize search text
        search_normalized = self.normalizer.normalize_for_matching(search_text)

        # Create text segments from words (sliding windows)
        segments = self._create_text_segments(words_data, search_text)

        if not segments:
            return []

        # Find fuzzy matches
        matches = []

        for segment in segments:
            segment_text = segment['text']
            segment_normalized = self.normalizer.normalize_for_matching(segment_text)

            # Calculate similarity
            score = self.scorer(search_normalized, segment_normalized)

            if score >= self.threshold:
                # Create match
                match = Match(
                    text=search_text,
                    bbox=segment['bbox'],
                    page_num=segment['page_num'],
                    confidence=score / 100.0,  # Normalize to 0-1
                    match_type="fuzzy",
                    metadata={
                        'matched_text': segment_text,
                        'similarity_score': score,
                        'word_count': segment['word_count'],
                        'page_width': segment['page_width'],
                        'page_height': segment['page_height'],
                        'scorer': self.scorer.__name__
                    }
                )
                matches.append(match)

        # Sort by confidence (descending)
        matches.sort(key=lambda m: m.confidence, reverse=True)

        return matches[:max_matches]

    def _create_text_segments(
        self,
        words_data: List[Dict[str, Any]],
        reference_text: str,
        tolerance: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Create text segments from words for fuzzy matching.

        Args:
            words_data: List of word dictionaries
            reference_text: Reference text to determine segment size
            tolerance: Size tolerance multiplier

        Returns:
            List of text segments with bounding boxes
        """
        # Estimate number of words in reference text
        ref_tokens = reference_text.split()
        ref_word_count = len(ref_tokens)

        # Calculate min and max segment sizes
        min_words = max(1, int(ref_word_count * (1 - tolerance)))
        max_words = int(ref_word_count * (1 + tolerance))

        segments = []

        # Create segments of varying sizes
        for window_size in range(min_words, max_words + 1):
            for i in range(len(words_data) - window_size + 1):
                segment_words = words_data[i:i + window_size]

                # Check if all words are on same page
                pages = set(w['page_num'] for w in segment_words)
                if len(pages) > 1:
                    continue

                # Combine words into text
                segment_text = ' '.join(w['text'] for w in segment_words)

                # Merge bounding boxes
                bboxes = [w['bbox'] for w in segment_words]
                merged_bbox = CoordinateNormalizer.merge_bboxes(bboxes)

                segment = {
                    'text': segment_text,
                    'bbox': merged_bbox,
                    'page_num': segment_words[0]['page_num'],
                    'word_count': len(segment_words),
                    'page_width': segment_words[0]['page_width'],
                    'page_height': segment_words[0]['page_height']
                }

                segments.append(segment)

        return segments

    def find_best_match(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]]
    ) -> Optional[Match]:
        """
        Find the best fuzzy match.

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries

        Returns:
            Best match or None
        """
        matches = self.find_matches(search_text, words_data, max_matches=1)

        return matches[0] if matches else None

    def find_with_multiple_strategies(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]]
    ) -> List[Match]:
        """
        Find matches using multiple fuzzy matching strategies.

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries

        Returns:
            Combined list of matches from all strategies
        """
        all_matches = []

        # Strategy 1: Standard ratio
        self.scorer = fuzz.ratio
        matches1 = self.find_matches(search_text, words_data, max_matches=5)
        all_matches.extend(matches1)

        # Strategy 2: Partial ratio (for substrings)
        self.scorer = fuzz.partial_ratio
        matches2 = self.find_matches(search_text, words_data, max_matches=5)
        all_matches.extend(matches2)

        # Strategy 3: Token sort ratio (ignore word order)
        self.scorer = fuzz.token_sort_ratio
        matches3 = self.find_matches(search_text, words_data, max_matches=5)
        all_matches.extend(matches3)

        # Strategy 4: Token set ratio (for partial matches)
        self.scorer = fuzz.token_set_ratio
        matches4 = self.find_matches(search_text, words_data, max_matches=5)
        all_matches.extend(matches4)

        # Remove duplicates (same bbox and page)
        unique_matches = []
        seen = set()

        for match in all_matches:
            key = (match.bbox, match.page_num)
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        # Sort by confidence
        unique_matches.sort(key=lambda m: m.confidence, reverse=True)

        return unique_matches

    def match_with_context(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        context_boost: float = 0.1
    ) -> List[Match]:
        """
        Find matches considering surrounding context.

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries
            context_before: Expected text before the search text
            context_after: Expected text after the search text
            context_boost: Confidence boost for matching context

        Returns:
            List of matches with context-adjusted confidence
        """
        matches = self.find_matches(search_text, words_data)

        # Adjust confidence based on context
        for match in matches:
            # TODO: Implement context checking
            # For now, just return matches as-is
            pass

        return matches


class MultiStrategyMatcher:
    """
    Combines exact and fuzzy matching with fallback strategies.
    """

    def __init__(
        self,
        exact_matcher=None,
        fuzzy_matcher=None,
        fuzzy_threshold: float = 80.0
    ):
        """
        Initialize multi-strategy matcher.

        Args:
            exact_matcher: ExactMatcher instance
            fuzzy_matcher: FuzzyMatcher instance
            fuzzy_threshold: Threshold for fuzzy matching
        """
        from .exact_matcher import ExactMatcher

        self.exact_matcher = exact_matcher or ExactMatcher()
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher(
            threshold=fuzzy_threshold
        )

    def find_best_match(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]]
    ) -> Optional[Match]:
        """
        Find best match using multiple strategies.

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries

        Returns:
            Best match or None
        """
        # Try exact match first
        exact_match = self.exact_matcher.find_best_match(search_text, words_data)
        if exact_match:
            logger.info(f"Found exact match for: {search_text}")
            return exact_match

        # Try fuzzy match
        fuzzy_match = self.fuzzy_matcher.find_best_match(search_text, words_data)
        if fuzzy_match:
            logger.info(
                f"Found fuzzy match for: {search_text} "
                f"(confidence: {fuzzy_match.confidence:.2f})"
            )
            return fuzzy_match

        logger.warning(f"No match found for: {search_text}")
        return None

    def find_all_matches(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        include_fuzzy: bool = True
    ) -> List[Match]:
        """
        Find all matches using multiple strategies.

        Args:
            search_text: Text to search for
            words_data: List of word dictionaries
            include_fuzzy: Whether to include fuzzy matches

        Returns:
            List of all matches
        """
        matches = []

        # Get exact matches
        exact_matches = self.exact_matcher.find_all_occurrences(
            search_text,
            words_data
        )
        matches.extend(exact_matches)

        # Get fuzzy matches if requested
        if include_fuzzy and not exact_matches:
            fuzzy_matches = self.fuzzy_matcher.find_with_multiple_strategies(
                search_text,
                words_data
            )
            matches.extend(fuzzy_matches)

        return matches
