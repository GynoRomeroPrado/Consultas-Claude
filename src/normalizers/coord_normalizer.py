"""
Coordinate normalization utilities for different bounding box formats.
"""

from typing import Tuple, List, Dict, Any, Literal
from dataclasses import dataclass


@dataclass
class BoundingBox:
    """Represents a bounding box with various coordinate formats."""

    x0: float  # Left
    y0: float  # Top
    x1: float  # Right
    y1: float  # Bottom

    @property
    def width(self) -> float:
        """Get width of bounding box."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Get height of bounding box."""
        return self.y1 - self.y0

    @property
    def center_x(self) -> float:
        """Get center X coordinate."""
        return (self.x0 + self.x1) / 2

    @property
    def center_y(self) -> float:
        """Get center Y coordinate."""
        return (self.y0 + self.y1) / 2

    @property
    def area(self) -> float:
        """Get area of bounding box."""
        return self.width * self.height

    def to_xyxy(self) -> Tuple[float, float, float, float]:
        """Convert to (x0, y0, x1, y1) format."""
        return (self.x0, self.y0, self.x1, self.y1)

    def to_xywh(self) -> Tuple[float, float, float, float]:
        """Convert to (x, y, width, height) format - COCO style."""
        return (self.x0, self.y0, self.width, self.height)

    def to_cxcywh(self) -> Tuple[float, float, float, float]:
        """Convert to (center_x, center_y, width, height) format."""
        return (self.center_x, self.center_y, self.width, self.height)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'x0': self.x0,
            'y0': self.y0,
            'x1': self.x1,
            'y1': self.y1,
            'width': self.width,
            'height': self.height
        }

    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if this box intersects with another."""
        return not (
            self.x1 < other.x0 or
            self.x0 > other.x1 or
            self.y1 < other.y0 or
            self.y0 > other.y1
        )

    def intersection_area(self, other: 'BoundingBox') -> float:
        """Calculate intersection area with another box."""
        if not self.intersects(other):
            return 0.0

        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)

        return (x1 - x0) * (y1 - y0)

    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union (IoU) with another box."""
        intersection = self.intersection_area(other)
        union = self.area + other.area - intersection

        if union == 0:
            return 0.0

        return intersection / union


class CoordinateNormalizer:
    """Handles coordinate normalization to different scales and formats."""

    @staticmethod
    def normalize_to_scale(
        bbox: Tuple[float, float, float, float],
        page_width: float,
        page_height: float,
        target_scale: int = 1000
    ) -> Tuple[int, int, int, int]:
        """
        Normalize coordinates to target scale (e.g., 0-1000 for LayoutLM).

        Args:
            bbox: Bounding box in (x0, y0, x1, y1) format
            page_width: Width of the page in original units
            page_height: Height of the page in original units
            target_scale: Target scale (default 1000 for LayoutLM)

        Returns:
            Normalized bounding box as integers
        """
        x0, y0, x1, y1 = bbox

        norm_x0 = int(target_scale * (x0 / page_width))
        norm_y0 = int(target_scale * (y0 / page_height))
        norm_x1 = int(target_scale * (x1 / page_width))
        norm_y1 = int(target_scale * (y1 / page_height))

        # Ensure coordinates are within bounds
        norm_x0 = max(0, min(norm_x0, target_scale))
        norm_y0 = max(0, min(norm_y0, target_scale))
        norm_x1 = max(0, min(norm_x1, target_scale))
        norm_y1 = max(0, min(norm_y1, target_scale))

        return (norm_x0, norm_y0, norm_x1, norm_y1)

    @staticmethod
    def denormalize_from_scale(
        bbox: Tuple[int, int, int, int],
        page_width: float,
        page_height: float,
        source_scale: int = 1000
    ) -> Tuple[float, float, float, float]:
        """
        Denormalize coordinates from scale back to original units.

        Args:
            bbox: Normalized bounding box
            page_width: Width of the page in original units
            page_height: Height of the page in original units
            source_scale: Source scale (default 1000 for LayoutLM)

        Returns:
            Denormalized bounding box
        """
        x0, y0, x1, y1 = bbox

        denorm_x0 = (x0 / source_scale) * page_width
        denorm_y0 = (y0 / source_scale) * page_height
        denorm_x1 = (x1 / source_scale) * page_width
        denorm_y1 = (y1 / source_scale) * page_height

        return (denorm_x0, denorm_y0, denorm_x1, denorm_y1)

    @staticmethod
    def convert_format(
        bbox: Tuple[float, ...],
        from_format: Literal["xyxy", "xywh", "cxcywh"],
        to_format: Literal["xyxy", "xywh", "cxcywh"]
    ) -> Tuple[float, float, float, float]:
        """
        Convert between different bounding box formats.

        Args:
            bbox: Input bounding box
            from_format: Current format
            to_format: Desired format

        Returns:
            Converted bounding box
        """
        # First convert to xyxy (canonical format)
        if from_format == "xywh":
            x, y, w, h = bbox
            x0, y0, x1, y1 = x, y, x + w, y + h
        elif from_format == "cxcywh":
            cx, cy, w, h = bbox
            x0, y0, x1, y1 = cx - w/2, cy - h/2, cx + w/2, cy + h/2
        else:  # xyxy
            x0, y0, x1, y1 = bbox

        # Then convert to target format
        if to_format == "xywh":
            return (x0, y0, x1 - x0, y1 - y0)
        elif to_format == "cxcywh":
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            w = x1 - x0
            h = y1 - y0
            return (cx, cy, w, h)
        else:  # xyxy
            return (x0, y0, x1, y1)

    @staticmethod
    def merge_bboxes(
        bboxes: List[Tuple[float, float, float, float]]
    ) -> Tuple[float, float, float, float]:
        """
        Merge multiple bounding boxes into a single bounding box.

        Args:
            bboxes: List of bounding boxes in (x0, y0, x1, y1) format

        Returns:
            Merged bounding box
        """
        if not bboxes:
            return (0, 0, 0, 0)

        x0 = min(bbox[0] for bbox in bboxes)
        y0 = min(bbox[1] for bbox in bboxes)
        x1 = max(bbox[2] for bbox in bboxes)
        y1 = max(bbox[3] for bbox in bboxes)

        return (x0, y0, x1, y1)

    @staticmethod
    def expand_bbox(
        bbox: Tuple[float, float, float, float],
        padding: float = 0,
        padding_percent: float = 0
    ) -> Tuple[float, float, float, float]:
        """
        Expand bounding box by padding.

        Args:
            bbox: Bounding box in (x0, y0, x1, y1) format
            padding: Absolute padding in all directions
            padding_percent: Padding as percentage of box size

        Returns:
            Expanded bounding box
        """
        x0, y0, x1, y1 = bbox

        if padding_percent > 0:
            width = x1 - x0
            height = y1 - y0
            pad_x = width * padding_percent
            pad_y = height * padding_percent
        else:
            pad_x = padding
            pad_y = padding

        return (
            x0 - pad_x,
            y0 - pad_y,
            x1 + pad_x,
            y1 + pad_y
        )

    @staticmethod
    def clip_bbox_to_page(
        bbox: Tuple[float, float, float, float],
        page_width: float,
        page_height: float
    ) -> Tuple[float, float, float, float]:
        """
        Clip bounding box to page boundaries.

        Args:
            bbox: Bounding box in (x0, y0, x1, y1) format
            page_width: Page width
            page_height: Page height

        Returns:
            Clipped bounding box
        """
        x0, y0, x1, y1 = bbox

        x0 = max(0, min(x0, page_width))
        y0 = max(0, min(y0, page_height))
        x1 = max(0, min(x1, page_width))
        y1 = max(0, min(y1, page_height))

        return (x0, y0, x1, y1)
