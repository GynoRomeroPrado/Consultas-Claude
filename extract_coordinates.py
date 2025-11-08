#!/usr/bin/env python3
"""
CLI script for PDF-JSON coordinate extraction.
"""

import argparse
import json
import sys
from pathlib import Path

from src.core.pipeline import CoordinateExtractionPipeline
from src.core.config import (
    PipelineConfig,
    MatchStrategy,
    ExportFormat,
    MatcherConfig,
    ExporterConfig
)


def main():
    parser = argparse.ArgumentParser(
        description='Extract bounding box coordinates from PDF using JSON fields',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python extract_coordinates.py document.pdf document.json -o output.json

  # Use fuzzy matching
  python extract_coordinates.py document.pdf document.json -o output.json --fuzzy --threshold 75

  # Export to LayoutLM format
  python extract_coordinates.py document.pdf document.json -o output.json --format layoutlm

  # Batch processing
  python extract_coordinates.py --batch input_dir/ output_dir/

  # Verbose mode
  python extract_coordinates.py document.pdf document.json -o output.json -v
        """
    )

    # Input arguments
    parser.add_argument('pdf', nargs='?', help='Path to PDF file')
    parser.add_argument('json', nargs='?', help='Path to JSON file (optional, auto-detected if same name)')

    # Output arguments
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--output-dir', help='Output directory for batch processing')

    # Matching strategy
    parser.add_argument(
        '--strategy',
        choices=['exact', 'fuzzy', 'auto', 'multiline'],
        default='auto',
        help='Matching strategy (default: auto)'
    )
    parser.add_argument(
        '--fuzzy',
        action='store_true',
        help='Use fuzzy matching (shortcut for --strategy fuzzy)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=80.0,
        help='Fuzzy matching threshold 0-100 (default: 80)'
    )

    # Export format
    parser.add_argument(
        '--format',
        choices=['json', 'csv', 'layoutlm', 'coco', 'pascal_voc', 'yolo'],
        default='json',
        help='Export format (default: json)'
    )

    # Batch processing
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch process all PDFs in directory'
    )

    # Other options
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--no-confidence',
        action='store_true',
        help='Exclude confidence scores from output'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.batch and not args.pdf:
        parser.error("PDF file is required (or use --batch)")

    # Determine strategy
    if args.fuzzy:
        strategy = MatchStrategy.FUZZY
    else:
        strategy = MatchStrategy[args.strategy.upper()]

    # Determine format
    export_format = ExportFormat[args.format.upper()]

    # Create configuration
    config = PipelineConfig(
        matcher=MatcherConfig(
            strategy=strategy,
            fuzzy_threshold=args.threshold
        ),
        exporter=ExporterConfig(
            format=export_format,
            include_confidence=not args.no_confidence
        ),
        verbose=args.verbose
    )

    # Create pipeline
    pipeline = CoordinateExtractionPipeline(config=config)

    try:
        if args.batch:
            # Batch processing
            if not args.pdf:
                parser.error("Input directory required for batch processing")

            input_dir = Path(args.pdf)
            output_dir = Path(args.output_dir or 'output')

            if not input_dir.is_dir():
                print(f"Error: {input_dir} is not a directory")
                sys.exit(1)

            # Find all PDF-JSON pairs
            pdf_files = list(input_dir.glob('*.pdf'))
            pairs = []

            for pdf_file in pdf_files:
                json_file = pdf_file.with_suffix('.json')
                if json_file.exists():
                    pairs.append((str(pdf_file), str(json_file)))

            if not pairs:
                print(f"No PDF-JSON pairs found in {input_dir}")
                sys.exit(1)

            print(f"Found {len(pairs)} PDF-JSON pairs")

            # Process batch
            results = pipeline.batch_process(pairs, str(output_dir))

            # Print summary
            print("\n" + "=" * 80)
            print("BATCH PROCESSING SUMMARY")
            print("=" * 80)

            successful = sum(1 for r in results if 'error' not in r)
            print(f"Successful: {successful}/{len(results)}")

            for i, result in enumerate(results, 1):
                pdf_name = Path(result['pdf_path']).stem

                if 'error' in result:
                    print(f"[{i}] ✗ {pdf_name}: {result['error']}")
                else:
                    stats = result['statistics']
                    print(
                        f"[{i}] ✓ {pdf_name}: "
                        f"{stats['match_rate']:.1f}% match rate, "
                        f"avg confidence: {stats['average_confidence']:.2f}"
                    )

        else:
            # Single file processing
            pdf_path = args.pdf
            json_path = args.json
            output_path = args.output

            if not output_path:
                # Auto-generate output path
                pdf_stem = Path(pdf_path).stem
                ext = '.json' if export_format == ExportFormat.JSON else '.csv'
                output_path = f"output/{pdf_stem}_annotations{ext}"

            # Process
            print(f"Processing: {pdf_path}")

            result = pipeline.process(
                pdf_path=pdf_path,
                json_path=json_path,
                output_path=output_path
            )

            # Print results
            print("\n" + "=" * 80)
            print("EXTRACTION RESULTS")
            print("=" * 80)

            stats = result['statistics']
            print(f"Total fields:      {stats['total_fields']}")
            print(f"Matched fields:    {stats['matched_fields']}")
            print(f"Unmatched fields:  {stats['unmatched_fields']}")
            print(f"Match rate:        {stats['match_rate']:.1f}%")
            print(f"Avg confidence:    {stats['average_confidence']:.4f}")

            if stats['match_types']:
                print(f"\nMatch types:")
                for match_type, count in stats['match_types'].items():
                    print(f"  {match_type}: {count}")

            print(f"\nPages with matches: {stats['pages_with_matches']}")
            print(f"Output saved to: {output_path}")

            if args.verbose and result['matches']:
                print("\n" + "=" * 80)
                print("MATCHED FIELDS")
                print("=" * 80)

                for match, field_name in zip(result['matches'], result['field_names']):
                    print(
                        f"  {field_name}: '{match.text}' "
                        f"(page {match.page_num}, confidence: {match.confidence:.2f})"
                    )

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
