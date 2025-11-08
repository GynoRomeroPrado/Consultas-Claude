"""
PDF text and coordinate extraction using PyMuPDF.
"""

import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Represents a block of text with coordinates."""
    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    page_num: int
    block_type: str = "text"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PDFPage:
    """Represents a PDF page with extracted content."""
    page_num: int
    width: float
    height: float
    text_blocks: List[TextBlock]
    full_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFExtractor:
    """Extract text and coordinates from PDF files using PyMuPDF."""

    def __init__(self, extract_images: bool = False):
        """
        Initialize PDF extractor.

        Args:
            extract_images: Whether to extract image information
        """
        self.extract_images = extract_images

    def extract(self, pdf_path: str) -> List[PDFPage]:
        """
        Extract all pages from a PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of PDFPage objects
        """
        pages = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                pdf_page = self._extract_page(page, page_num)
                pages.append(pdf_page)

            doc.close()

        except Exception as e:
            logger.error(f"Error extracting PDF {pdf_path}: {e}")
            raise

        return pages

    def _extract_page(self, page: fitz.Page, page_num: int) -> PDFPage:
        """
        Extract content from a single page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            PDFPage object
        """
        # Get page dimensions
        rect = page.rect
        width, height = rect.width, rect.height

        # Extract text blocks
        text_blocks = self._extract_text_blocks(page, page_num)

        # Get full text
        full_text = page.get_text()

        # Get metadata
        metadata = {
            'rotation': page.rotation,
            'has_images': len(page.get_images()) > 0 if self.extract_images else None
        }

        return PDFPage(
            page_num=page_num,
            width=width,
            height=height,
            text_blocks=text_blocks,
            full_text=full_text,
            metadata=metadata
        )

    def _extract_text_blocks(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """
        Extract text blocks with coordinates.

        Args:
            page: PyMuPDF page object
            page_num: Page number

        Returns:
            List of TextBlock objects
        """
        text_blocks = []

        # Use "dict" mode for detailed hierarchical structure
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            if block["type"] == 0:  # Text block
                block_text = self._extract_block_text(block)
                if block_text.strip():
                    bbox = tuple(block["bbox"])
                    text_block = TextBlock(
                        text=block_text,
                        bbox=bbox,
                        page_num=page_num,
                        block_type="text",
                        metadata={
                            "lines": len(block.get("lines", [])),
                            "number": block.get("number", -1)
                        }
                    )
                    text_blocks.append(text_block)

        return text_blocks

    def _extract_block_text(self, block: Dict[str, Any]) -> str:
        """
        Extract text from a block dictionary.

        Args:
            block: Block dictionary from PyMuPDF

        Returns:
            Extracted text
        """
        text_parts = []

        for line in block.get("lines", []):
            line_text = ""
            for span in line.get("spans", []):
                line_text += span.get("text", "")
            text_parts.append(line_text)

        return "\n".join(text_parts)

    def extract_words(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract word-level information with coordinates.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of word dictionaries with bbox and metadata
        """
        words_data = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                rect = page.rect
                page_width, page_height = rect.width, rect.height

                # Extract words
                words = page.get_text("words")

                for word in words:
                    # word format: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                    word_data = {
                        'text': word[4],
                        'bbox': (word[0], word[1], word[2], word[3]),
                        'page_num': page_num,
                        'page_width': page_width,
                        'page_height': page_height,
                        'block_no': word[5],
                        'line_no': word[6],
                        'word_no': word[7]
                    }
                    words_data.append(word_data)

            doc.close()

        except Exception as e:
            logger.error(f"Error extracting words from PDF {pdf_path}: {e}")
            raise

        return words_data

    def search_text(
        self,
        pdf_path: str,
        search_term: str,
        case_sensitive: bool = False,
        use_quads: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for text in PDF and return bounding boxes.

        Args:
            pdf_path: Path to PDF file
            search_term: Text to search for
            case_sensitive: Whether to use case-sensitive search
            use_quads: Return quadrilaterals instead of rectangles (for rotated text)

        Returns:
            List of matches with bounding boxes
        """
        matches = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                rect = page.rect
                page_width, page_height = rect.width, rect.height

                # Search for text
                flags = 0 if case_sensitive else fitz.TEXT_PRESERVE_WHITESPACE

                if use_quads:
                    # Returns list of quads for rotated text
                    quads = page.search_for(search_term, quads=True)
                    for quad in quads:
                        # Convert quad to bbox
                        bbox = quad.rect
                        match_data = {
                            'text': search_term,
                            'bbox': (bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                            'page_num': page_num,
                            'page_width': page_width,
                            'page_height': page_height,
                            'type': 'quad'
                        }
                        matches.append(match_data)
                else:
                    # Returns list of rectangles
                    rects = page.search_for(search_term)
                    for rect in rects:
                        match_data = {
                            'text': search_term,
                            'bbox': (rect.x0, rect.y0, rect.x1, rect.y1),
                            'page_num': page_num,
                            'page_width': page_width,
                            'page_height': page_height,
                            'type': 'rect'
                        }
                        matches.append(match_data)

            doc.close()

        except Exception as e:
            logger.error(f"Error searching PDF {pdf_path}: {e}")
            raise

        return matches

    def get_page_dimensions(self, pdf_path: str) -> List[Tuple[float, float]]:
        """
        Get dimensions of all pages.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of (width, height) tuples
        """
        dimensions = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                rect = page.rect
                dimensions.append((rect.width, rect.height))

            doc.close()

        except Exception as e:
            logger.error(f"Error getting page dimensions from {pdf_path}: {e}")
            raise

        return dimensions

    def extract_text_in_bbox(
        self,
        pdf_path: str,
        page_num: int,
        bbox: Tuple[float, float, float, float]
    ) -> str:
        """
        Extract text within a specific bounding box.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            bbox: Bounding box (x0, y0, x1, y1)

        Returns:
            Extracted text
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]

            # Create rectangle
            rect = fitz.Rect(bbox)

            # Extract text in rectangle
            text = page.get_text(clip=rect)

            doc.close()

            return text

        except Exception as e:
            logger.error(f"Error extracting text in bbox from {pdf_path}: {e}")
            raise
