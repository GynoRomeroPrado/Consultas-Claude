"""
Unit tests for the coordinate extraction pipeline.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.normalizers.text_normalizer import TextNormalizer
from src.normalizers.coord_normalizer import CoordinateNormalizer, BoundingBox
from src.core.config import PipelineConfig, MatchStrategy, ExportFormat


class TestTextNormalizer:
    """Tests for TextNormalizer."""

    def test_basic_normalization(self):
        normalizer = TextNormalizer()
        text = "  Hello   World  "
        result = normalizer.normalize(text)
        assert result == "hello world"

    def test_unicode_normalization(self):
        normalizer = TextNormalizer()
        text = "café"
        result = normalizer.normalize(text)
        assert "café" in result or "cafe" in result

    def test_normalize_for_matching(self):
        normalizer = TextNormalizer()
        text = "Hello\nWorld\r\nTest"
        result = normalizer.normalize_for_matching(text)
        assert "\n" not in result
        assert "\r" not in result

    def test_remove_accents(self):
        text = "José María"
        result = TextNormalizer.remove_accents(text)
        assert result == "Jose Maria"

    def test_is_mostly_numeric(self):
        assert TextNormalizer.is_mostly_numeric("12345")
        assert TextNormalizer.is_mostly_numeric("123abc45")
        assert not TextNormalizer.is_mostly_numeric("hello")


class TestCoordinateNormalizer:
    """Tests for CoordinateNormalizer."""

    def test_bounding_box_properties(self):
        bbox = BoundingBox(x0=10, y0=20, x1=50, y1=60)
        assert bbox.width == 40
        assert bbox.height == 40
        assert bbox.center_x == 30
        assert bbox.center_y == 40
        assert bbox.area == 1600

    def test_bbox_to_xywh(self):
        bbox = BoundingBox(x0=10, y0=20, x1=50, y1=60)
        xywh = bbox.to_xywh()
        assert xywh == (10, 20, 40, 40)

    def test_normalize_to_scale(self):
        normalizer = CoordinateNormalizer()
        bbox = (100, 200, 300, 400)
        page_width = 1000
        page_height = 1000
        target_scale = 1000

        result = normalizer.normalize_to_scale(
            bbox, page_width, page_height, target_scale
        )

        assert result == (100, 200, 300, 400)

    def test_normalize_to_scale_different_page_size(self):
        normalizer = CoordinateNormalizer()
        bbox = (50, 100, 150, 200)
        page_width = 500
        page_height = 500
        target_scale = 1000

        result = normalizer.normalize_to_scale(
            bbox, page_width, page_height, target_scale
        )

        assert result == (100, 200, 300, 400)

    def test_merge_bboxes(self):
        normalizer = CoordinateNormalizer()
        bboxes = [
            (10, 10, 20, 20),
            (15, 15, 25, 25),
            (20, 20, 30, 30)
        ]

        merged = normalizer.merge_bboxes(bboxes)
        assert merged == (10, 10, 30, 30)

    def test_expand_bbox(self):
        normalizer = CoordinateNormalizer()
        bbox = (10, 10, 20, 20)

        expanded = normalizer.expand_bbox(bbox, padding=5)
        assert expanded == (5, 5, 25, 25)

    def test_bbox_intersection(self):
        bbox1 = BoundingBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BoundingBox(x0=5, y0=5, x1=15, y1=15)

        assert bbox1.intersects(bbox2)
        assert bbox1.intersection_area(bbox2) == 25

    def test_bbox_iou(self):
        bbox1 = BoundingBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BoundingBox(x0=0, y0=0, x1=10, y1=10)

        # Perfect overlap
        assert bbox1.iou(bbox2) == 1.0


class TestConfig:
    """Tests for configuration system."""

    def test_default_config(self):
        config = PipelineConfig()
        assert config.matcher.strategy == MatchStrategy.AUTO
        assert config.exporter.format == ExportFormat.JSON

    def test_config_to_dict(self):
        config = PipelineConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert 'matcher' in config_dict
        assert 'exporter' in config_dict

    def test_config_from_dict(self):
        config_dict = {
            'matcher': {
                'strategy': 'fuzzy',
                'fuzzy_threshold': 85.0
            },
            'exporter': {
                'format': 'layoutlm'
            }
        }

        config = PipelineConfig.from_dict(config_dict)
        assert config.matcher.strategy == MatchStrategy.FUZZY
        assert config.matcher.fuzzy_threshold == 85.0
        assert config.exporter.format == ExportFormat.LAYOUTLM


class TestJSONParser:
    """Tests for JSON parser."""

    def test_flatten_dict(self):
        from src.extractors.json_parser import JSONParser

        parser = JSONParser(flatten_nested=True)
        data = {
            "name": "John",
            "address": {
                "street": "Main St",
                "city": "New York"
            }
        }

        flattened = parser._flatten_dict(data)

        assert "name" in flattened
        assert "address.street" in flattened
        assert "address.city" in flattened

    def test_extract_text_values(self):
        from src.extractors.json_parser import JSONParser
        import tempfile
        import json

        data = {
            "field1": "value1",
            "field2": "value2",
            "field3": 123
        }

        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        parser = JSONParser()
        text_values = parser.extract_text_values(temp_path)

        assert "value1" in text_values
        assert "value2" in text_values
        assert "123" in text_values

        # Cleanup
        Path(temp_path).unlink()


class TestMatchers:
    """Tests for matching algorithms."""

    def test_exact_matcher_simple(self):
        from src.matchers.exact_matcher import ExactMatcher

        matcher = ExactMatcher()

        # Create mock words data
        words_data = [
            {'text': 'Hello', 'bbox': (0, 0, 50, 10), 'page_num': 0,
             'page_width': 100, 'page_height': 100},
            {'text': 'World', 'bbox': (60, 0, 100, 10), 'page_num': 0,
             'page_width': 100, 'page_height': 100}
        ]

        match = matcher.find_best_match("Hello World", words_data)

        assert match is not None
        assert match.text == "Hello World"
        assert match.confidence == 1.0

    def test_fuzzy_matcher_threshold(self):
        from src.matchers.fuzzy_matcher import FuzzyMatcher

        matcher = FuzzyMatcher(threshold=80.0)

        words_data = [
            {'text': 'Helo', 'bbox': (0, 0, 50, 10), 'page_num': 0,
             'page_width': 100, 'page_height': 100},
            {'text': 'World', 'bbox': (60, 0, 100, 10), 'page_num': 0,
             'page_width': 100, 'page_height': 100}
        ]

        # Should match "Helo" to "Hello" with fuzzy matching
        matches = matcher.find_matches("Hello", words_data, max_matches=1)

        assert len(matches) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
