"""
Export bounding boxes in COCO format for object detection.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..matchers.exact_matcher import Match

logger = logging.getLogger(__name__)


class COCOExporter:
    """Export annotations in COCO format."""

    def __init__(
        self,
        dataset_name: str = "PDF Field Dataset",
        description: str = "PDF field bounding box annotations"
    ):
        """
        Initialize COCO exporter.

        Args:
            dataset_name: Name of the dataset
            description: Description of the dataset
        """
        self.dataset_name = dataset_name
        self.description = description

    def export(
        self,
        matches: List[Match],
        field_names: List[str],
        pdf_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Export matches to COCO format.

        Args:
            matches: List of Match objects
            field_names: List of field names corresponding to matches
            pdf_path: Path to source PDF file
            output_path: Path to save output JSON

        Returns:
            Dictionary in COCO format
        """
        if len(matches) != len(field_names):
            raise ValueError(
                f"Number of matches ({len(matches)}) must equal "
                f"number of field names ({len(field_names)})"
            )

        # Create categories (unique field names)
        unique_fields = sorted(set(field_names))
        categories = []

        for i, field_name in enumerate(unique_fields, start=1):
            categories.append({
                'id': i,
                'name': field_name,
                'supercategory': 'field'
            })

        # Create category name to ID mapping
        category_map = {cat['name']: cat['id'] for cat in categories}

        # Group matches by page to create images
        pages = {}
        for match in matches:
            if match.page_num not in pages:
                pages[match.page_num] = {
                    'width': match.metadata.get('page_width', 0),
                    'height': match.metadata.get('page_height', 0)
                }

        # Create images list
        images = []
        for page_num in sorted(pages.keys()):
            page_data = pages[page_num]
            images.append({
                'id': page_num + 1,  # 1-indexed
                'file_name': f"{pdf_path}_page_{page_num}.png",
                'width': int(page_data['width']),
                'height': int(page_data['height']),
                'page_num': page_num
            })

        # Create annotations
        annotations = []
        annotation_id = 1

        for match, field_name in zip(matches, field_names):
            # Convert bbox to COCO format (x, y, width, height)
            x0, y0, x1, y1 = match.bbox
            bbox_coco = [
                float(x0),
                float(y0),
                float(x1 - x0),  # width
                float(y1 - y0)   # height
            ]

            area = bbox_coco[2] * bbox_coco[3]

            annotation = {
                'id': annotation_id,
                'image_id': match.page_num + 1,  # Match with image ID
                'category_id': category_map[field_name],
                'bbox': bbox_coco,
                'area': area,
                'iscrowd': 0,
                'attributes': {
                    'text': match.text,
                    'confidence': match.confidence,
                    'match_type': match.match_type
                }
            }

            annotations.append(annotation)
            annotation_id += 1

        # Create COCO structure
        coco_data = {
            'info': {
                'description': self.description,
                'url': '',
                'version': '1.0',
                'year': datetime.now().year,
                'contributor': '',
                'date_created': datetime.now().isoformat()
            },
            'licenses': [
                {
                    'id': 1,
                    'name': 'Unknown',
                    'url': ''
                }
            ],
            'images': images,
            'annotations': annotations,
            'categories': categories
        }

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(coco_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported COCO format to {output_path}")
        logger.info(
            f"Dataset stats: {len(images)} images, "
            f"{len(annotations)} annotations, "
            f"{len(categories)} categories"
        )

        return coco_data

    def export_segmentation(
        self,
        matches: List[Match],
        field_names: List[str],
        pdf_path: str,
        output_path: str,
        use_bbox_as_segmentation: bool = True
    ) -> Dict[str, Any]:
        """
        Export with segmentation masks (using bboxes as masks).

        Args:
            matches: List of Match objects
            field_names: List of field names
            pdf_path: Path to source PDF
            output_path: Path to save output
            use_bbox_as_segmentation: Convert bbox to polygon segmentation

        Returns:
            Dictionary in COCO format with segmentations
        """
        # Get base COCO data
        coco_data = self.export(matches, field_names, pdf_path, output_path + '.tmp')

        # Add segmentation to each annotation
        for annotation in coco_data['annotations']:
            bbox = annotation['bbox']
            x, y, w, h = bbox

            # Create polygon from bbox (clockwise from top-left)
            segmentation = [[
                x, y,           # top-left
                x + w, y,       # top-right
                x + w, y + h,   # bottom-right
                x, y + h        # bottom-left
            ]]

            annotation['segmentation'] = segmentation

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(coco_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported COCO format with segmentation to {output_path}")

        return coco_data
