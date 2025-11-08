"""
Main pipeline for PDF-JSON coordinate extraction.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm

from .config import (
    PipelineConfig,
    MatchStrategy,
    ExportFormat,
    DEFAULT_CONFIG
)
from ..extractors.pdf_extractor import PDFExtractor
from ..extractors.json_parser import JSONParser
from ..normalizers.text_normalizer import TextNormalizer
from ..matchers.exact_matcher import ExactMatcher, Match
from ..matchers.fuzzy_matcher import FuzzyMatcher, MultiStrategyMatcher
from ..matchers.multiline_matcher import MultilineMatcher
from ..exporters.layoutlm_exporter import LayoutLMExporter
from ..exporters.coco_exporter import COCOExporter
from ..exporters.custom_exporter import CustomExporter

logger = logging.getLogger(__name__)


class CoordinateExtractionPipeline:
    """Main pipeline for extracting bounding boxes from PDF-JSON pairs."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize pipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config or DEFAULT_CONFIG

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all pipeline components."""
        # PDF extractor
        self.pdf_extractor = PDFExtractor(
            extract_images=self.config.pdf_extractor.extract_images
        )

        # JSON parser
        self.json_parser = JSONParser(
            flatten_nested=self.config.flatten_json,
            separator=self.config.json_separator,
            ignore_keys=self.config.ignore_json_keys
        )

        # Text normalizer
        self.normalizer = TextNormalizer(
            unicode_form=self.config.normalizer.unicode_form,
            lowercase=self.config.normalizer.lowercase,
            remove_extra_whitespace=self.config.normalizer.remove_extra_whitespace,
            remove_punctuation=self.config.normalizer.remove_punctuation,
            custom_replacements=self.config.normalizer.custom_replacements
        )

        # Matchers
        self.exact_matcher = ExactMatcher(
            normalizer=self.normalizer,
            case_sensitive=self.config.matcher.case_sensitive
        )

        self.fuzzy_matcher = FuzzyMatcher(
            normalizer=self.normalizer,
            threshold=self.config.matcher.fuzzy_threshold
        )

        self.multi_matcher = MultiStrategyMatcher(
            exact_matcher=self.exact_matcher,
            fuzzy_matcher=self.fuzzy_matcher,
            fuzzy_threshold=self.config.matcher.fuzzy_threshold
        )

        self.multiline_matcher = MultilineMatcher(
            normalizer=self.normalizer
        )

        # Exporters
        self.layoutlm_exporter = LayoutLMExporter(
            target_scale=self.config.exporter.target_scale
        )

        self.coco_exporter = COCOExporter()

        self.custom_exporter = CustomExporter()

    def process(
        self,
        pdf_path: str,
        json_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a PDF-JSON pair and extract coordinates.

        Args:
            pdf_path: Path to PDF file
            json_path: Path to JSON file (auto-detected if None)
            output_path: Output path (auto-generated if None)

        Returns:
            Dictionary with results and statistics
        """
        logger.info(f"Processing PDF: {pdf_path}")

        # Find matching JSON if not provided
        if json_path is None:
            json_path = self.json_parser.find_matching_json(pdf_path)
            if json_path is None:
                raise FileNotFoundError(f"No matching JSON found for {pdf_path}")

        logger.info(f"Using JSON: {json_path}")

        # Extract PDF content
        logger.info("Extracting PDF content...")
        words_data = self.pdf_extractor.extract_words(pdf_path)

        logger.info(f"Extracted {len(words_data)} words from PDF")

        # Parse JSON fields
        logger.info("Parsing JSON fields...")
        fields = self.json_parser.extract_fields(json_path)

        logger.info(f"Found {len(fields)} fields in JSON")

        # Match fields to coordinates
        logger.info("Matching fields to coordinates...")
        matches, field_names = self._match_fields(fields, words_data, pdf_path)

        logger.info(f"Matched {len(matches)}/{len(fields)} fields")

        # Generate statistics
        stats = self._generate_statistics(matches, fields)

        # Export results
        if output_path:
            logger.info("Exporting results...")
            export_result = self._export_results(
                matches,
                field_names,
                pdf_path,
                output_path
            )
            stats['export_path'] = export_result

        return {
            'matches': matches,
            'field_names': field_names,
            'statistics': stats
        }

    def _match_fields(
        self,
        fields: Dict[str, str],
        words_data: List[Dict[str, Any]],
        pdf_path: str
    ) -> Tuple[List[Match], List[str]]:
        """
        Match JSON fields to PDF coordinates.

        Args:
            fields: Dictionary of field_name -> value
            words_data: Word-level PDF data
            pdf_path: Path to PDF file

        Returns:
            Tuple of (matches, field_names)
        """
        matches = []
        field_names = []

        # Use tqdm for progress bar if verbose
        iterator = tqdm(fields.items(), desc="Matching fields") if self.config.verbose else fields.items()

        for field_name, field_value in iterator:
            if not field_value or not field_value.strip():
                logger.debug(f"Skipping empty field: {field_name}")
                continue

            # Try to find match using configured strategy
            match = self._find_match(field_value, words_data, pdf_path)

            if match:
                matches.append(match)
                field_names.append(field_name)

                if self.config.verbose:
                    logger.info(
                        f"✓ Matched '{field_name}': {field_value} "
                        f"(confidence: {match.confidence:.2f})"
                    )
            else:
                if self.config.verbose:
                    logger.warning(f"✗ No match for '{field_name}': {field_value}")

        return matches, field_names

    def _find_match(
        self,
        search_text: str,
        words_data: List[Dict[str, Any]],
        pdf_path: str
    ) -> Optional[Match]:
        """
        Find match using configured strategy.

        Args:
            search_text: Text to search for
            words_data: Word-level PDF data
            pdf_path: Path to PDF file

        Returns:
            Match object or None
        """
        strategy = self.config.matcher.strategy

        # Check for multiline text
        is_multiline = '\n' in search_text or '\r' in search_text

        if is_multiline and self.config.matcher.use_multiline:
            # Use PyMuPDF search for multiline
            search_results = self.pdf_extractor.search_text(
                pdf_path,
                search_text,
                case_sensitive=self.config.matcher.case_sensitive
            )

            if search_results:
                matches = self.multiline_matcher.match_from_pymupdf_search(
                    search_results,
                    search_text
                )
                if matches:
                    return matches[0]

        # Regular matching strategies
        if strategy == MatchStrategy.EXACT:
            return self.exact_matcher.find_best_match(
                search_text,
                words_data,
                prefer_first=self.config.matcher.prefer_first_match
            )

        elif strategy == MatchStrategy.FUZZY:
            return self.fuzzy_matcher.find_best_match(search_text, words_data)

        elif strategy == MatchStrategy.AUTO:
            return self.multi_matcher.find_best_match(search_text, words_data)

        elif strategy == MatchStrategy.MULTILINE:
            # Try multiline matching
            search_results = self.pdf_extractor.search_text(pdf_path, search_text)
            if search_results:
                matches = self.multiline_matcher.match_from_pymupdf_search(
                    search_results,
                    search_text
                )
                if matches:
                    return matches[0]

        return None

    def _export_results(
        self,
        matches: List[Match],
        field_names: List[str],
        pdf_path: str,
        output_path: str
    ) -> str:
        """
        Export results in configured format.

        Args:
            matches: List of matches
            field_names: List of field names
            pdf_path: Path to PDF file
            output_path: Output path

        Returns:
            Path to exported file
        """
        export_format = self.config.exporter.format

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if export_format == ExportFormat.LAYOUTLM:
            self.layoutlm_exporter.export(
                matches,
                field_names,
                output_path,
                include_confidence=self.config.exporter.include_confidence
            )

        elif export_format == ExportFormat.COCO:
            self.coco_exporter.export(
                matches,
                field_names,
                pdf_path,
                output_path
            )

        elif export_format == ExportFormat.JSON:
            self.custom_exporter.export_json(
                matches,
                field_names,
                output_path,
                include_metadata=self.config.exporter.include_metadata
            )

        elif export_format == ExportFormat.CSV:
            self.custom_exporter.export_csv(
                matches,
                field_names,
                output_path
            )

        elif export_format == ExportFormat.PASCAL_VOC:
            output_dir = str(Path(output_path).parent / 'pascal_voc')
            self.custom_exporter.export_pascal_voc(
                matches,
                field_names,
                pdf_path,
                output_dir
            )
            return output_dir

        elif export_format == ExportFormat.YOLO:
            output_dir = str(Path(output_path).parent / 'yolo')
            self.custom_exporter.export_yolo(
                matches,
                field_names,
                output_dir
            )
            return output_dir

        return output_path

    def _generate_statistics(
        self,
        matches: List[Match],
        fields: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Generate statistics about matching results.

        Args:
            matches: List of matches
            fields: Original fields dictionary

        Returns:
            Dictionary with statistics
        """
        total_fields = len(fields)
        matched_fields = len(matches)
        match_rate = (matched_fields / total_fields * 100) if total_fields > 0 else 0

        # Group by match type
        match_types = {}
        for match in matches:
            match_type = match.match_type
            match_types[match_type] = match_types.get(match_type, 0) + 1

        # Calculate average confidence
        avg_confidence = (
            sum(m.confidence for m in matches) / len(matches)
            if matches else 0
        )

        # Group by page
        pages = set(m.page_num for m in matches)

        stats = {
            'total_fields': total_fields,
            'matched_fields': matched_fields,
            'unmatched_fields': total_fields - matched_fields,
            'match_rate': round(match_rate, 2),
            'average_confidence': round(avg_confidence, 4),
            'match_types': match_types,
            'pages_with_matches': len(pages),
            'pages': sorted(pages)
        }

        return stats

    def batch_process(
        self,
        pdf_json_pairs: List[Tuple[str, str]],
        output_dir: str
    ) -> List[Dict[str, Any]]:
        """
        Process multiple PDF-JSON pairs.

        Args:
            pdf_json_pairs: List of (pdf_path, json_path) tuples
            output_dir: Output directory

        Returns:
            List of results for each pair
        """
        results = []

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        for i, (pdf_path, json_path) in enumerate(tqdm(pdf_json_pairs, desc="Processing documents")):
            try:
                # Generate output path
                pdf_name = Path(pdf_path).stem
                output_path = str(Path(output_dir) / f"{pdf_name}_annotations.json")

                # Process
                result = self.process(pdf_path, json_path, output_path)
                result['pdf_path'] = pdf_path
                result['json_path'] = json_path

                results.append(result)

                logger.info(f"[{i+1}/{len(pdf_json_pairs)}] Processed: {pdf_name}")

            except Exception as e:
                logger.error(f"Error processing {pdf_path}: {e}")
                results.append({
                    'pdf_path': pdf_path,
                    'json_path': json_path,
                    'error': str(e)
                })

        return results
