"""
Basic usage example for PDF-JSON coordinate extraction.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.pipeline import CoordinateExtractionPipeline
from src.core.config import (
    PipelineConfig,
    MatchStrategy,
    ExportFormat,
    MatcherConfig,
    ExporterConfig
)


def example_1_basic_usage():
    """Example 1: Basic usage with default configuration."""
    print("=" * 80)
    print("Example 1: Basic Usage")
    print("=" * 80)

    # Create pipeline with default config
    pipeline = CoordinateExtractionPipeline()

    # Process a PDF-JSON pair
    # Note: Replace these paths with your actual files
    pdf_path = "sample.pdf"
    json_path = "sample.json"
    output_path = "output/sample_annotations.json"

    try:
        result = pipeline.process(
            pdf_path=pdf_path,
            json_path=json_path,
            output_path=output_path
        )

        # Print statistics
        print("\nResults:")
        print(f"  Matched fields: {result['statistics']['matched_fields']}")
        print(f"  Match rate: {result['statistics']['match_rate']}%")
        print(f"  Average confidence: {result['statistics']['average_confidence']}")
        print(f"  Output saved to: {output_path}")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please provide valid PDF and JSON files.")


def example_2_custom_config():
    """Example 2: Using custom configuration."""
    print("\n" + "=" * 80)
    print("Example 2: Custom Configuration")
    print("=" * 80)

    # Create custom configuration
    config = PipelineConfig(
        matcher=MatcherConfig(
            strategy=MatchStrategy.AUTO,
            fuzzy_threshold=75.0,
            prefer_first_match=True
        ),
        exporter=ExporterConfig(
            format=ExportFormat.LAYOUTLM,
            include_confidence=True,
            target_scale=1000
        ),
        verbose=True
    )

    # Create pipeline with custom config
    pipeline = CoordinateExtractionPipeline(config=config)

    # Process document
    pdf_path = "sample.pdf"
    output_path = "output/sample_layoutlm.json"

    try:
        result = pipeline.process(pdf_path=pdf_path, output_path=output_path)
        print(f"\nExported to LayoutLM format: {output_path}")

    except FileNotFoundError as e:
        print(f"\nError: {e}")


def example_3_different_export_formats():
    """Example 3: Export to different formats."""
    print("\n" + "=" * 80)
    print("Example 3: Different Export Formats")
    print("=" * 80)

    pdf_path = "sample.pdf"
    json_path = "sample.json"

    formats = [
        (ExportFormat.JSON, "output/sample_custom.json"),
        (ExportFormat.CSV, "output/sample.csv"),
        (ExportFormat.LAYOUTLM, "output/sample_layoutlm.json"),
        (ExportFormat.COCO, "output/sample_coco.json"),
    ]

    for export_format, output_path in formats:
        print(f"\nExporting to {export_format.value}...")

        config = PipelineConfig(
            exporter=ExporterConfig(format=export_format)
        )

        pipeline = CoordinateExtractionPipeline(config=config)

        try:
            result = pipeline.process(
                pdf_path=pdf_path,
                json_path=json_path,
                output_path=output_path
            )
            print(f"  ✓ Saved to: {output_path}")

        except FileNotFoundError:
            print(f"  ✗ Files not found")
            break


def example_4_batch_processing():
    """Example 4: Batch processing multiple files."""
    print("\n" + "=" * 80)
    print("Example 4: Batch Processing")
    print("=" * 80)

    # List of PDF-JSON pairs
    pdf_json_pairs = [
        ("document1.pdf", "document1.json"),
        ("document2.pdf", "document2.json"),
        ("document3.pdf", "document3.json"),
    ]

    # Create pipeline
    pipeline = CoordinateExtractionPipeline()

    # Batch process
    output_dir = "output/batch"

    try:
        results = pipeline.batch_process(pdf_json_pairs, output_dir)

        # Print summary
        print("\nBatch Processing Summary:")
        successful = sum(1 for r in results if 'error' not in r)
        print(f"  Successful: {successful}/{len(results)}")

        for i, result in enumerate(results, 1):
            if 'error' in result:
                print(f"  [{i}] ✗ {result['pdf_path']}: {result['error']}")
            else:
                stats = result['statistics']
                print(f"  [{i}] ✓ {result['pdf_path']}: {stats['match_rate']}% match rate")

    except Exception as e:
        print(f"\nError: {e}")


def example_5_fuzzy_matching():
    """Example 5: Using fuzzy matching for OCR errors."""
    print("\n" + "=" * 80)
    print("Example 5: Fuzzy Matching")
    print("=" * 80)

    # Configuration optimized for fuzzy matching
    config = PipelineConfig(
        matcher=MatcherConfig(
            strategy=MatchStrategy.FUZZY,
            fuzzy_threshold=70.0,  # Lower threshold for more lenient matching
        ),
        exporter=ExporterConfig(
            format=ExportFormat.JSON,
            include_confidence=True  # Show confidence scores
        ),
        verbose=True
    )

    pipeline = CoordinateExtractionPipeline(config=config)

    pdf_path = "sample_ocr.pdf"  # PDF with potential OCR errors
    output_path = "output/sample_fuzzy.json"

    try:
        result = pipeline.process(pdf_path=pdf_path, output_path=output_path)

        # Show matches with confidence scores
        print("\nMatches with confidence scores:")
        for match, field_name in zip(result['matches'], result['field_names']):
            print(f"  {field_name}: {match.text} (confidence: {match.confidence:.2f})")

    except FileNotFoundError as e:
        print(f"\nError: {e}")


def example_6_direct_component_usage():
    """Example 6: Using components directly for advanced control."""
    print("\n" + "=" * 80)
    print("Example 6: Direct Component Usage")
    print("=" * 80)

    from src.extractors.pdf_extractor import PDFExtractor
    from src.extractors.json_parser import JSONParser
    from src.matchers.fuzzy_matcher import MultiStrategyMatcher
    from src.exporters.custom_exporter import CustomExporter

    pdf_path = "sample.pdf"
    json_path = "sample.json"

    try:
        # 1. Extract PDF words
        print("1. Extracting PDF words...")
        pdf_extractor = PDFExtractor()
        words_data = pdf_extractor.extract_words(pdf_path)
        print(f"   Found {len(words_data)} words")

        # 2. Parse JSON
        print("2. Parsing JSON fields...")
        json_parser = JSONParser()
        fields = json_parser.extract_fields(json_path)
        print(f"   Found {len(fields)} fields")

        # 3. Match fields
        print("3. Matching fields...")
        matcher = MultiStrategyMatcher()
        matches = []
        field_names = []

        for field_name, field_value in fields.items():
            match = matcher.find_best_match(field_value, words_data)
            if match:
                matches.append(match)
                field_names.append(field_name)
                print(f"   ✓ Matched: {field_name}")

        # 4. Export
        print("4. Exporting...")
        exporter = CustomExporter()
        exporter.export_json(matches, field_names, "output/direct_usage.json")
        print("   ✓ Exported to output/direct_usage.json")

    except FileNotFoundError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    print("PDF-JSON Coordinate Extraction Examples")
    print("=" * 80)

    # Run examples
    example_1_basic_usage()
    example_2_custom_config()
    example_3_different_export_formats()
    example_4_batch_processing()
    example_5_fuzzy_matching()
    example_6_direct_component_usage()

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
