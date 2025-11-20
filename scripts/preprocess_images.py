#!/usr/bin/env python3
"""
Script de Preprocesamiento de Imágenes
Aplica operaciones morfológicas y deskewing a facturas.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessing.pipeline import create_high_resolution_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Preprocesar imágenes de facturas"
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
        help="Directorio para guardar imágenes procesadas"
    )
    parser.add_argument(
        "--file-pattern",
        type=str,
        default="*.png",
        help="Patrón de archivos a procesar (default: *.png)"
    )
    parser.add_argument(
        "--target-width",
        type=int,
        default=1920,
        help="Ancho objetivo en píxeles"
    )
    parser.add_argument(
        "--target-height",
        type=int,
        default=2560,
        help="Alto objetivo en píxeles"
    )
    parser.add_argument(
        "--kernel-size",
        type=int,
        nargs=2,
        default=[3, 3],
        help="Tamaño del kernel morfológico (ancho alto)"
    )
    parser.add_argument(
        "--deskew-method",
        type=str,
        choices=["projection", "hough"],
        default="projection",
        help="Método de deskewing"
    )
    parser.add_argument(
        "--no-contrast-enhancement",
        action="store_true",
        help="Deshabilitar mejora de contraste"
    )
    parser.add_argument(
        "--no-noise-removal",
        action="store_true",
        help="Deshabilitar eliminación de ruido"
    )
    parser.add_argument(
        "--save-metadata",
        action="store_true",
        help="Guardar metadata del procesamiento"
    )

    args = parser.parse_args()

    # Crear pipeline
    print("Creando pipeline de preprocesamiento...")
    from src.preprocessing.pipeline import InvoicePreprocessingPipeline

    pipeline = InvoicePreprocessingPipeline(
        target_size=(args.target_width, args.target_height),
        morphology_kernel=tuple(args.kernel_size),
        deskew_method=args.deskew_method,
        enhance_contrast=not args.no_contrast_enhancement,
        remove_noise=not args.no_noise_removal
    )

    # Procesar directorio
    print(f"Procesando imágenes de {args.input_dir}...")
    stats = pipeline.process_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        file_pattern=args.file_pattern,
        save_metadata=args.save_metadata
    )

    # Mostrar estadísticas
    print("\n" + "="*60)
    print("Procesamiento completado!")
    print("="*60)
    print(f"Total de archivos: {stats['total_files']}")
    print(f"Procesados exitosamente: {stats['processed']}")
    print(f"Fallidos: {stats['failed']}")
    print(f"Ángulo promedio de inclinación: {stats['average_skew_angle']:.2f}°")

    if stats['failed'] > 0:
        print("\nArchivos fallidos:")
        for fail in stats['failed_files']:
            print(f"  - {fail['file']}: {fail['error']}")

    print(f"\nImágenes procesadas guardadas en: {args.output_dir}")


if __name__ == "__main__":
    main()
