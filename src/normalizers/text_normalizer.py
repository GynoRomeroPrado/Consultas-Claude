"""
Text normalization utilities for handling special characters, Unicode, and whitespace.
"""

import re
import unicodedata
from typing import Optional


class TextNormalizer:
    """Handles text normalization for consistent matching."""

    def __init__(
        self,
        unicode_form: str = "NFKC",
        lowercase: bool = True,
        remove_extra_whitespace: bool = True,
        remove_punctuation: bool = False,
        custom_replacements: Optional[dict] = None
    ):
        """
        Initialize text normalizer.

        Args:
            unicode_form: Unicode normalization form (NFC, NFD, NFKC, NFKD)
            lowercase: Convert to lowercase
            remove_extra_whitespace: Replace multiple spaces with single space
            remove_punctuation: Remove punctuation characters
            custom_replacements: Dictionary of custom text replacements
        """
        self.unicode_form = unicode_form
        self.lowercase = lowercase
        self.remove_extra_whitespace = remove_extra_whitespace
        self.remove_punctuation = remove_punctuation
        self.custom_replacements = custom_replacements or {}

    def normalize(self, text: str) -> str:
        """
        Normalize text according to configured rules.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Unicode normalization (handles ligatures, special chars, etc.)
        text = unicodedata.normalize(self.unicode_form, text)

        # Custom replacements
        for old, new in self.custom_replacements.items():
            text = text.replace(old, new)

        # Lowercase
        if self.lowercase:
            text = text.lower()

        # Remove punctuation if requested
        if self.remove_punctuation:
            text = re.sub(r'[^\w\s]', '', text)

        # Handle whitespace
        if self.remove_extra_whitespace:
            # Replace multiple whitespace with single space
            text = re.sub(r'\s+', ' ', text)
            # Strip leading/trailing whitespace
            text = text.strip()

        return text

    def normalize_for_matching(self, text: str) -> str:
        """
        Normalize text specifically for fuzzy matching.
        More aggressive normalization.

        Args:
            text: Input text

        Returns:
            Normalized text optimized for matching
        """
        text = self.normalize(text)

        # Remove common PDF artifacts
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        text = text.replace('\t', ' ')

        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Remove extra whitespace again after all replacements
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def extract_alphanumeric(self, text: str) -> str:
        """
        Extract only alphanumeric characters and spaces.
        Useful for very fuzzy matching.

        Args:
            text: Input text

        Returns:
            Text with only alphanumeric characters
        """
        text = self.normalize(text)
        return re.sub(r'[^a-z0-9\s]', '', text, flags=re.IGNORECASE)

    def tokenize(self, text: str) -> list[str]:
        """
        Split text into tokens (words).

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        text = self.normalize(text)
        return text.split()

    @staticmethod
    def is_mostly_numeric(text: str) -> bool:
        """Check if text is mostly numeric."""
        if not text:
            return False
        numeric_chars = sum(c.isdigit() for c in text)
        return numeric_chars / len(text) > 0.5

    @staticmethod
    def is_mostly_alphabetic(text: str) -> bool:
        """Check if text is mostly alphabetic."""
        if not text:
            return False
        alpha_chars = sum(c.isalpha() for c in text)
        return alpha_chars / len(text) > 0.5

    @staticmethod
    def remove_accents(text: str) -> str:
        """
        Remove accents from text.

        Args:
            text: Input text

        Returns:
            Text without accents
        """
        # Normalize to NFD (decomposed form)
        nfd_form = unicodedata.normalize('NFD', text)
        # Filter out combining characters (accents)
        return ''.join(char for char in nfd_form
                      if unicodedata.category(char) != 'Mn')


# Pre-configured normalizers for common use cases
DEFAULT_NORMALIZER = TextNormalizer()

STRICT_NORMALIZER = TextNormalizer(
    unicode_form="NFKC",
    lowercase=True,
    remove_extra_whitespace=True,
    remove_punctuation=False
)

FUZZY_NORMALIZER = TextNormalizer(
    unicode_form="NFKC",
    lowercase=True,
    remove_extra_whitespace=True,
    remove_punctuation=True
)
