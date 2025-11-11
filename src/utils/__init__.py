"""
Utilidades para procesamiento de documentos.
"""

from .parallel_processor import (
    ParallelDocumentProcessor,
    find_document_pairs,
    batch_process_documents,
    parallel_ocr_extraction
)

__all__ = [
    'ParallelDocumentProcessor',
    'find_document_pairs',
    'batch_process_documents',
    'parallel_ocr_extraction'
]
