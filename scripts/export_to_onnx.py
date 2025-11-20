#!/usr/bin/env python3
"""
Script de Exportación a ONNX
Exporta modelo entrenado a formato ONNX con cuantización.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimization.onnx_exporter import export_model_to_onnx


def main():
    parser = argparse.ArgumentParser(
        description="Exportar modelo Donut a formato ONNX"
    )

    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Ruta al modelo entrenado"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./onnx_models",
        help="Directorio de salida para modelos ONNX"
    )
    parser.add_argument(
        "--no-quantize",
        action="store_true",
        help="No aplicar cuantización INT8"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Ejecutar benchmark de rendimiento"
    )
    parser.add_argument(
        "--test-image",
        type=str,
        help="Imagen de prueba para benchmark"
    )

    args = parser.parse_args()

    # Exportar modelo
    print("="*60)
    print("Exportación a ONNX")
    print("="*60)
    print(f"Modelo: {args.model_path}")
    print(f"Salida: {args.output_dir}")
    print(f"Cuantización: {'No' if args.no_quantize else 'Sí (INT8)'}")
    print("="*60 + "\n")

    paths = export_model_to_onnx(
        model_path=args.model_path,
        output_dir=args.output_dir,
        quantize=not args.no_quantize
    )

    # Mostrar rutas
    print("\nModelos exportados:")
    for name, path in paths.items():
        file_size = Path(path).stat().st_size / (1024 * 1024)
        print(f"  {name}: {path} ({file_size:.2f} MB)")

    # Benchmark opcional
    if args.benchmark:
        if not args.test_image:
            print("\nERROR: --test-image requerido para benchmark")
            return

        print("\n" + "="*60)
        print("Ejecutando benchmark...")
        print("="*60)

        import cv2
        from transformers import DonutProcessor
        from src.optimization.onnx_exporter import ONNXInferenceEngine

        # Cargar imagen de prueba
        test_image = cv2.imread(args.test_image)
        if test_image is None:
            print(f"ERROR: No se pudo cargar {args.test_image}")
            return

        # Cargar processor
        processor = DonutProcessor.from_pretrained(args.model_path)

        # Crear motor de inferencia
        encoder_path = paths.get("encoder_quantized", paths["encoder"])
        decoder_path = paths.get("decoder_quantized", paths["decoder"])

        engine = ONNXInferenceEngine(
            encoder_path=encoder_path,
            decoder_path=decoder_path,
            processor=processor,
            use_gpu=False
        )

        # Ejecutar benchmark
        results = engine.benchmark(test_image, num_iterations=10)

        print("\nResultados del benchmark:")
        print(f"  Tiempo promedio: {results['mean_time']*1000:.2f} ms")
        print(f"  Desviación estándar: {results['std_time']*1000:.2f} ms")
        print(f"  Tiempo mínimo: {results['min_time']*1000:.2f} ms")
        print(f"  Tiempo máximo: {results['max_time']*1000:.2f} ms")
        print(f"  Throughput: {results['throughput']:.2f} imágenes/segundo")

    print("\n" + "="*60)
    print("Exportación completada exitosamente!")
    print("="*60)


if __name__ == "__main__":
    main()
