#!/usr/bin/env python3
"""
Script para validar calidad de dataset antes de entrenar LayoutLMv3.

Detecta:
- Coordenadas mal normalizadas o fuera de límites
- Bboxes degeneradas
- Texto vacío
- Baja confianza
- Otros problemas que arruinan el entrenamiento
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.validation.dataset_validator import DatasetValidator
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nAsegúrate de tener la estructura de directorios correcta")
    sys.exit(1)


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Valida calidad de dataset para LayoutLMv3"
    )

    parser.add_argument(
        "dataset_dir",
        help="Directorio con archivos *_coordenadas.json o *_layoutlm.json"
    )

    parser.add_argument(
        "--confianza-minima",
        type=float,
        default=0.70,
        help="Umbral mínimo de confianza (default: 0.70)"
    )

    parser.add_argument(
        "--area-minima",
        type=int,
        default=10,
        help="Área mínima de bbox en escala 0-1000 (default: 10)"
    )

    parser.add_argument(
        "--umbral-error",
        type=float,
        default=0.05,
        help="% máximo de errores para aprobar dataset (default: 0.05 = 5%%)"
    )

    parser.add_argument(
        "--export-json",
        help="Exportar reporte de validación a JSON"
    )

    parser.add_argument(
        "--silencioso",
        action="store_true",
        help="No mostrar reporte detallado"
    )

    args = parser.parse_args()

    # Crear validador
    validator = DatasetValidator(
        confianza_minima=args.confianza_minima,
        area_minima=args.area_minima,
        umbral_error_critico=args.umbral_error
    )

    # Validar dataset
    try:
        metricas = validator.validar_dataset(
            args.dataset_dir,
            verbose=not args.silencioso
        )

        # Exportar a JSON si se solicita
        if args.export_json:
            import json
            output_path = Path(args.export_json)
            with open(output_path, 'w', encoding='utf-8') as f:
                # Convertir a JSON-serializable
                metricas_json = {
                    'total_documentos': metricas['total_documentos'],
                    'total_campos': metricas['total_campos'],
                    'num_errores_criticos': len(metricas['errores_criticos']),
                    'num_advertencias': len(metricas['advertencias']),
                    'estadisticas_finales': metricas.get('estadisticas_finales', {}),
                    'apto_entrenamiento': metricas['apto_entrenamiento'],
                    'errores_criticos': metricas['errores_criticos'][:50],  # Primeros 50
                    'advertencias': metricas['advertencias'][:50],
                    'documentos_problematicos': metricas['documentos_problematicos']
                }
                json.dump(metricas_json, f, indent=2, ensure_ascii=False)

            print(f"\n💾 Reporte exportado a: {output_path}")

        # Exit code basado en validación
        if metricas['apto_entrenamiento']:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error durante validación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
