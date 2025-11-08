"""
Custom flexible exporter for various output formats.
"""

import json
import csv
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from ..matchers.exact_matcher import Match

logger = logging.getLogger(__name__)


class CustomExporter:
    """Flexible exporter supporting multiple custom formats."""

    def export_json(
        self,
        matches: List[Match],
        field_names: List[str],
        output_path: str,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Export to simple JSON format.

        Args:
            matches: List of Match objects
            field_names: List of field names
            output_path: Path to save output
            include_metadata: Include match metadata

        Returns:
            Dictionary with annotations
        """
        annotations = []

        for match, field_name in zip(matches, field_names):
            annotation = {
                'field_name': field_name,
                'text': match.text,
                'bbox': {
                    'x0': match.bbox[0],
                    'y0': match.bbox[1],
                    'x1': match.bbox[2],
                    'y1': match.bbox[3]
                },
                'page': match.page_num,
                'confidence': match.confidence,
                'match_type': match.match_type
            }

            if include_metadata:
                annotation['metadata'] = match.metadata

            annotations.append(annotation)

        output_data = {
            'format': 'custom',
            'total_fields': len(annotations),
            'annotations': annotations
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported custom JSON to {output_path}")

        return output_data

    def export_csv(
        self,
        matches: List[Match],
        field_names: List[str],
        output_path: str
    ) -> None:
        """
        Export to CSV format.

        Args:
            matches: List of Match objects
            field_names: List of field names
            output_path: Path to save CSV
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'field_name',
                'text',
                'x0',
                'y0',
                'x1',
                'y1',
                'page',
                'confidence',
                'match_type',
                'page_width',
                'page_height'
            ])

            # Data
            for match, field_name in zip(matches, field_names):
                writer.writerow([
                    field_name,
                    match.text,
                    match.bbox[0],
                    match.bbox[1],
                    match.bbox[2],
                    match.bbox[3],
                    match.page_num,
                    match.confidence,
                    match.match_type,
                    match.metadata.get('page_width', ''),
                    match.metadata.get('page_height', '')
                ])

        logger.info(f"Exported CSV to {output_path}")

    def export_pascal_voc(
        self,
        matches: List[Match],
        field_names: List[str],
        pdf_path: str,
        output_dir: str
    ) -> None:
        """
        Export to Pascal VOC XML format (one file per page).

        Args:
            matches: List of Match objects
            field_names: List of field names
            pdf_path: Path to source PDF
            output_dir: Directory to save XML files
        """
        from xml.etree.ElementTree import Element, SubElement, ElementTree
        from xml.dom import minidom

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Group by page
        pages_data = {}

        for match, field_name in zip(matches, field_names):
            page_num = match.page_num

            if page_num not in pages_data:
                pages_data[page_num] = {
                    'width': match.metadata.get('page_width', 0),
                    'height': match.metadata.get('page_height', 0),
                    'objects': []
                }

            pages_data[page_num]['objects'].append({
                'name': field_name,
                'bbox': match.bbox,
                'text': match.text
            })

        # Create XML for each page
        for page_num, page_data in pages_data.items():
            # Create root element
            annotation = Element('annotation')

            # Filename
            filename = SubElement(annotation, 'filename')
            filename.text = f"{Path(pdf_path).stem}_page_{page_num}.png"

            # Size
            size = SubElement(annotation, 'size')
            width = SubElement(size, 'width')
            width.text = str(int(page_data['width']))
            height = SubElement(size, 'height')
            height.text = str(int(page_data['height']))
            depth = SubElement(size, 'depth')
            depth.text = '3'

            # Objects
            for obj in page_data['objects']:
                obj_elem = SubElement(annotation, 'object')

                name = SubElement(obj_elem, 'name')
                name.text = obj['name']

                bndbox = SubElement(obj_elem, 'bndbox')
                xmin = SubElement(bndbox, 'xmin')
                xmin.text = str(int(obj['bbox'][0]))
                ymin = SubElement(bndbox, 'ymin')
                ymin.text = str(int(obj['bbox'][1]))
                xmax = SubElement(bndbox, 'xmax')
                xmax.text = str(int(obj['bbox'][2]))
                ymax = SubElement(bndbox, 'ymax')
                ymax.text = str(int(obj['bbox'][3]))

            # Pretty print XML
            xml_str = minidom.parseString(
                ElementTree.tostring(annotation, encoding='unicode')
            ).toprettyxml(indent='  ')

            # Save to file
            output_file = Path(output_dir) / f"page_{page_num}.xml"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)

        logger.info(f"Exported Pascal VOC XML to {output_dir}")

    def export_yolo(
        self,
        matches: List[Match],
        field_names: List[str],
        output_dir: str,
        class_names: Optional[List[str]] = None
    ) -> None:
        """
        Export to YOLO format (normalized center x, y, width, height).

        Args:
            matches: List of Match objects
            field_names: List of field names
            output_dir: Directory to save YOLO files
            class_names: Optional list of class names
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Create class mapping
        if class_names is None:
            class_names = sorted(set(field_names))

        class_map = {name: i for i, name in enumerate(class_names)}

        # Save class names
        with open(Path(output_dir) / 'classes.txt', 'w') as f:
            for name in class_names:
                f.write(f"{name}\n")

        # Group by page
        pages_data = {}

        for match, field_name in zip(matches, field_names):
            page_num = match.page_num

            if page_num not in pages_data:
                pages_data[page_num] = {
                    'width': match.metadata.get('page_width', 1),
                    'height': match.metadata.get('page_height', 1),
                    'boxes': []
                }

            # Convert to YOLO format (normalized center x, y, w, h)
            x0, y0, x1, y1 = match.bbox
            page_width = pages_data[page_num]['width']
            page_height = pages_data[page_num]['height']

            # Center coordinates
            center_x = ((x0 + x1) / 2) / page_width
            center_y = ((y0 + y1) / 2) / page_height

            # Dimensions
            width = (x1 - x0) / page_width
            height = (y1 - y0) / page_height

            class_id = class_map.get(field_name, 0)

            pages_data[page_num]['boxes'].append(
                f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}"
            )

        # Save YOLO files for each page
        for page_num, page_data in pages_data.items():
            output_file = Path(output_dir) / f"page_{page_num}.txt"

            with open(output_file, 'w') as f:
                for box in page_data['boxes']:
                    f.write(f"{box}\n")

        logger.info(f"Exported YOLO format to {output_dir}")

    def export_visualization_data(
        self,
        matches: List[Match],
        field_names: List[str],
        output_path: str
    ) -> Dict[str, Any]:
        """
        Export data for visualization purposes.

        Args:
            matches: List of Match objects
            field_names: List of field names
            output_path: Path to save JSON

        Returns:
            Dictionary with visualization data
        """
        viz_data = {
            'pages': {}
        }

        for match, field_name in zip(matches, field_names):
            page_num = match.page_num

            if page_num not in viz_data['pages']:
                viz_data['pages'][page_num] = {
                    'page_num': page_num,
                    'width': match.metadata.get('page_width', 0),
                    'height': match.metadata.get('page_height', 0),
                    'fields': []
                }

            field_data = {
                'name': field_name,
                'text': match.text,
                'bbox': list(match.bbox),
                'confidence': match.confidence,
                'match_type': match.match_type,
                'color': self._get_color_for_field(field_name)
            }

            viz_data['pages'][page_num]['fields'].append(field_data)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(viz_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported visualization data to {output_path}")

        return viz_data

    def _get_color_for_field(self, field_name: str) -> str:
        """
        Get consistent color for field name.

        Args:
            field_name: Field name

        Returns:
            Hex color code
        """
        # Simple hash-based color generation
        hash_val = hash(field_name)
        r = (hash_val & 0xFF0000) >> 16
        g = (hash_val & 0x00FF00) >> 8
        b = hash_val & 0x0000FF

        return f"#{r:02x}{g:02x}{b:02x}"
