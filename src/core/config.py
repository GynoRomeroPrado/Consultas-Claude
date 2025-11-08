"""
Configuration settings for the PDF-JSON coordinate extraction system.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class MatchStrategy(Enum):
    """Matching strategy options."""
    EXACT = "exact"
    FUZZY = "fuzzy"
    MULTILINE = "multiline"
    AUTO = "auto"  # Try exact first, then fuzzy


class ExportFormat(Enum):
    """Export format options."""
    LAYOUTLM = "layoutlm"
    COCO = "coco"
    PASCAL_VOC = "pascal_voc"
    YOLO = "yolo"
    JSON = "json"
    CSV = "csv"


@dataclass
class NormalizerConfig:
    """Configuration for text normalization."""
    unicode_form: str = "NFKC"
    lowercase: bool = True
    remove_extra_whitespace: bool = True
    remove_punctuation: bool = False
    custom_replacements: dict = field(default_factory=dict)


@dataclass
class MatcherConfig:
    """Configuration for matching."""
    strategy: MatchStrategy = MatchStrategy.AUTO
    case_sensitive: bool = False
    fuzzy_threshold: float = 80.0
    use_multiline: bool = True
    max_matches_per_field: int = 1
    prefer_first_match: bool = True


@dataclass
class ExporterConfig:
    """Configuration for export."""
    format: ExportFormat = ExportFormat.JSON
    output_dir: str = "output"
    include_confidence: bool = True
    include_metadata: bool = True
    normalize_coords: bool = False
    target_scale: int = 1000  # For LayoutLM


@dataclass
class PDFExtractorConfig:
    """Configuration for PDF extraction."""
    extract_images: bool = False
    use_word_level: bool = True
    search_case_sensitive: bool = False
    use_quads_for_rotated: bool = False


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""
    # Normalizer settings
    normalizer: NormalizerConfig = field(default_factory=NormalizerConfig)

    # Matcher settings
    matcher: MatcherConfig = field(default_factory=MatcherConfig)

    # Exporter settings
    exporter: ExporterConfig = field(default_factory=ExporterConfig)

    # PDF extractor settings
    pdf_extractor: PDFExtractorConfig = field(default_factory=PDFExtractorConfig)

    # JSON parser settings
    flatten_json: bool = True
    json_separator: str = "."
    ignore_json_keys: List[str] = field(default_factory=list)

    # General settings
    verbose: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'PipelineConfig':
        """
        Create config from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            PipelineConfig instance
        """
        # Parse nested configs
        normalizer_dict = config_dict.get('normalizer', {})
        matcher_dict = config_dict.get('matcher', {})
        exporter_dict = config_dict.get('exporter', {})
        pdf_extractor_dict = config_dict.get('pdf_extractor', {})

        # Handle enum conversions
        if 'strategy' in matcher_dict:
            matcher_dict['strategy'] = MatchStrategy(matcher_dict['strategy'])

        if 'format' in exporter_dict:
            exporter_dict['format'] = ExportFormat(exporter_dict['format'])

        return cls(
            normalizer=NormalizerConfig(**normalizer_dict),
            matcher=MatcherConfig(**matcher_dict),
            exporter=ExporterConfig(**exporter_dict),
            pdf_extractor=PDFExtractorConfig(**pdf_extractor_dict),
            flatten_json=config_dict.get('flatten_json', True),
            json_separator=config_dict.get('json_separator', '.'),
            ignore_json_keys=config_dict.get('ignore_json_keys', []),
            verbose=config_dict.get('verbose', False),
            log_level=config_dict.get('log_level', 'INFO')
        )

    def to_dict(self) -> dict:
        """
        Convert config to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            'normalizer': {
                'unicode_form': self.normalizer.unicode_form,
                'lowercase': self.normalizer.lowercase,
                'remove_extra_whitespace': self.normalizer.remove_extra_whitespace,
                'remove_punctuation': self.normalizer.remove_punctuation,
                'custom_replacements': self.normalizer.custom_replacements
            },
            'matcher': {
                'strategy': self.matcher.strategy.value,
                'case_sensitive': self.matcher.case_sensitive,
                'fuzzy_threshold': self.matcher.fuzzy_threshold,
                'use_multiline': self.matcher.use_multiline,
                'max_matches_per_field': self.matcher.max_matches_per_field,
                'prefer_first_match': self.matcher.prefer_first_match
            },
            'exporter': {
                'format': self.exporter.format.value,
                'output_dir': self.exporter.output_dir,
                'include_confidence': self.exporter.include_confidence,
                'include_metadata': self.exporter.include_metadata,
                'normalize_coords': self.exporter.normalize_coords,
                'target_scale': self.exporter.target_scale
            },
            'pdf_extractor': {
                'extract_images': self.pdf_extractor.extract_images,
                'use_word_level': self.pdf_extractor.use_word_level,
                'search_case_sensitive': self.pdf_extractor.search_case_sensitive,
                'use_quads_for_rotated': self.pdf_extractor.use_quads_for_rotated
            },
            'flatten_json': self.flatten_json,
            'json_separator': self.json_separator,
            'ignore_json_keys': self.ignore_json_keys,
            'verbose': self.verbose,
            'log_level': self.log_level
        }


# Default configurations
DEFAULT_CONFIG = PipelineConfig()

STRICT_MATCHING_CONFIG = PipelineConfig(
    matcher=MatcherConfig(
        strategy=MatchStrategy.EXACT,
        fuzzy_threshold=95.0
    )
)

FUZZY_MATCHING_CONFIG = PipelineConfig(
    matcher=MatcherConfig(
        strategy=MatchStrategy.FUZZY,
        fuzzy_threshold=70.0
    )
)

LAYOUTLM_CONFIG = PipelineConfig(
    exporter=ExporterConfig(
        format=ExportFormat.LAYOUTLM,
        normalize_coords=True,
        target_scale=1000
    )
)

COCO_CONFIG = PipelineConfig(
    exporter=ExporterConfig(
        format=ExportFormat.COCO
    )
)
