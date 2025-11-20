#!/usr/bin/env python3
"""
Script de Entrenamiento Multi-Fase para Donut
Ejecuta el entrenamiento estratégico completo siguiendo la hoja de ruta.
"""

import argparse
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model.donut_config import (
    create_high_resolution_config,
    create_training_config
)
from src.model.trainer import create_trainer


def main():
    parser = argparse.ArgumentParser(
        description="Entrenar modelo Donut para facturas peruanas"
    )

    # Argumentos de datos
    parser.add_argument(
        "--synthetic-data-dir",
        type=str,
        required=True,
        help="Directorio con imágenes sintéticas/augmentadas"
    )
    parser.add_argument(
        "--real-data-dir",
        type=str,
        required=True,
        help="Directorio con imágenes reales"
    )
    parser.add_argument(
        "--val-data-dir",
        type=str,
        help="Directorio con datos de validación (opcional)"
    )

    # Argumentos de modelo
    parser.add_argument(
        "--image-width",
        type=int,
        default=1920,
        help="Ancho de imagen objetivo"
    )
    parser.add_argument(
        "--image-height",
        type=int,
        default=2560,
        help="Alto de imagen objetivo"
    )

    # Argumentos de entrenamiento
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./checkpoints",
        help="Directorio para guardar checkpoints"
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=30,
        help="Número total de epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="Tamaño de batch"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=3e-5,
        help="Learning rate"
    )

    # Argumentos de fases
    parser.add_argument(
        "--phase1-epochs",
        type=int,
        default=15,
        help="Epochs para fase 1 (sintético)"
    )
    parser.add_argument(
        "--phase2-epochs",
        type=int,
        default=10,
        help="Epochs para fase 2 (mixto)"
    )
    parser.add_argument(
        "--phase3-epochs",
        type=int,
        default=5,
        help="Epochs para fase 3 (real)"
    )

    parser.add_argument(
        "--skip-phase1",
        action="store_true",
        help="Saltar fase 1"
    )
    parser.add_argument(
        "--skip-phase2",
        action="store_true",
        help="Saltar fase 2"
    )
    parser.add_argument(
        "--skip-phase3",
        action="store_true",
        help="Saltar fase 3"
    )

    args = parser.parse_args()

    # Crear configuraciones
    print("Configurando modelo...")
    model_config = create_high_resolution_config(
        width=args.image_width,
        height=args.image_height
    )

    training_config = create_training_config(
        output_dir=args.output_dir,
        num_epochs=args.num_epochs,
        batch_size=args.batch_size
    )

    # Ajustar configuración de fases
    training_config.learning_rate = args.learning_rate
    training_config.phase1_epochs = args.phase1_epochs
    training_config.phase2_epochs = args.phase2_epochs
    training_config.phase3_epochs = args.phase3_epochs
    training_config.phase1_synthetic_only = not args.skip_phase1
    training_config.phase2_mixed_data = not args.skip_phase2
    training_config.phase3_real_only = not args.skip_phase3

    # TODO: Cargar datasets reales aquí
    # Por ahora, placeholder
    print("NOTA: Debes implementar la carga de datasets personalizada")
    print("Los datasets deben ser objetos torch.utils.data.Dataset")

    synthetic_dataset = None  # TODO: Implementar
    real_dataset = None       # TODO: Implementar
    val_dataset = None        # TODO: Implementar

    if synthetic_dataset is None or real_dataset is None:
        print("\nERROR: Datasets no implementados.")
        print("Por favor, implementa la carga de tus datasets en este script.")
        print("Consulta la documentación de Transformers para crear datasets personalizados.")
        return

    # Crear trainer
    print("Inicializando trainer...")
    trainer = create_trainer(model_config, training_config)

    # Entrenar
    print("\nIniciando entrenamiento multi-fase...")
    metrics = trainer.train_all_phases(
        synthetic_dataset=synthetic_dataset,
        real_dataset=real_dataset,
        val_dataset=val_dataset
    )

    # Guardar métricas
    import json
    metrics_file = Path(args.output_dir) / "training_metrics.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"\nEntrenamiento completado!")
    print(f"Modelo final guardado en: {args.output_dir}/final_model")
    print(f"Métricas guardadas en: {metrics_file}")


if __name__ == "__main__":
    main()
