#!/usr/bin/env python3
"""
Script de Augmentación de Dataset
Genera variantes sintéticas usando Augraphy.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.augmentation.augraphy_pipeline import InvoiceAugmentationPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Augmentar dataset de facturas con Augraphy"
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directorio con imágenes originales"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directorio para guardar imágenes augmentadas"
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=3,
        help="Número de variantes por imagen (default: 3)"
    )
    parser.add_argument(
        "--intensity",
        type=str,
        choices=["light", "medium", "heavy"],
        default="medium",
        help="Intensidad de augmentación"
    )
    parser.add_argument(
        "--file-pattern",
        type=str,
        default="*.png",
        help="Patrón de archivos a procesar"
    )
    parser.add_argument(
        "--no-dot-matrix",
        action="store_true",
        help="Deshabilitar simulación de impresión matricial"
    )
    parser.add_argument(
        "--no-faded-paper",
        action="store_true",
        help="Deshabilitar simulación de papel desvanecido"
    )
    parser.add_argument(
        "--no-worn-ribbon",
        action="store_true",
        help="Deshabilitar simulación de cinta gastada"
    )

    args = parser.parse_args()

    # Crear pipeline
    print("Creando pipeline de augmentación...")
    pipeline = InvoiceAugmentationPipeline(
        intensity=args.intensity,
        simulate_dot_matrix=not args.no_dot_matrix,
        simulate_faded_paper=not args.no_faded_paper,
        simulate_worn_ribbon=not args.no_worn_ribbon
    )

    # Augmentar dataset
    print(f"Augmentando dataset de {args.input_dir}...")
    print(f"Generando {args.variants} variantes por imagen...")

    stats = pipeline.augment_dataset(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        variants_per_image=args.variants,
        file_pattern=args.file_pattern
    )

    # Mostrar estadísticas
    print("\n" + "="*60)
    print("Augmentación completada!")
    print("="*60)
    print(f"Imágenes originales: {stats['original_images']}")
    print(f"Variantes por imagen: {stats['variants_per_image']}")
    print(f"Total generadas: {stats['total_generated']}")
    print(f"Fallidas: {stats['failed']}")
    print(f"Dataset final: {stats['original_images'] + stats['total_generated']} imágenes")
    print(f"\nImágenes augmentadas guardadas en: {args.output_dir}")

    # Calcular factor de aumento
    factor = (stats['total_generated'] + stats['original_images']) / max(stats['original_images'], 1)
    print(f"Factor de aumento: {factor:.1f}x")


if __name__ == "__main__":
    main()
