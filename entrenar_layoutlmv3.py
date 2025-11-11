#!/usr/bin/env python3
"""
Script de entrenamiento básico para LayoutLMv3.

Fine-tuning de LayoutLMv3 para extracción de campos de facturas.
"""

import sys
import json
import torch
from pathlib import Path
from datetime import datetime

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from transformers import (
        LayoutLMv3ForTokenClassification,
        LayoutLMv3Processor,
        TrainingArguments,
        Trainer
    )
    from src.training.layoutlmv3_integration import (
        LayoutLMv3Dataset,
        create_dataloader,
        prepare_for_training
    )
    DEPS_OK = True
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nInstala las dependencias:")
    print("  pip install transformers torch")
    DEPS_OK = False


def entrenar_modelo(
    dataset_dir: str,
    images_dir: str,
    output_dir: str = "modelo_entrenado",
    model_name: str = "microsoft/layoutlmv3-base",
    epochs: int = 10,
    batch_size: int = 4,
    learning_rate: float = 5e-5,
    usar_gpu: bool = True
):
    """
    Entrena modelo LayoutLMv3 para extracción de campos.

    Args:
        dataset_dir: Directorio con archivos *_avanzado.json
        images_dir: Directorio con imágenes de páginas PDF
        output_dir: Directorio donde guardar modelo entrenado
        model_name: Modelo base a usar
        epochs: Número de épocas de entrenamiento
        batch_size: Tamaño de batch
        learning_rate: Tasa de aprendizaje
        usar_gpu: Usar GPU si está disponible
    """

    print("="*80)
    print("ENTRENAMIENTO DE LAYOUTLMV3")
    print("="*80)
    print(f"Dataset: {dataset_dir}")
    print(f"Modelo base: {model_name}")
    print(f"Épocas: {epochs}")
    print(f"Batch size: {batch_size}")
    print(f"Learning rate: {learning_rate}")
    print(f"GPU: {'Sí' if usar_gpu and torch.cuda.is_available() else 'No'}")
    print()

    # 1. Preparar dataset
    print("📊 Preparando dataset...")

    dataset_file, campo_to_id, id_to_campo = prepare_for_training(
        dataset_dir,
        images_dir,
        output_dir,
        model_name=model_name
    )

    num_labels = len(campo_to_id)
    print(f"   Número de labels: {num_labels}")
    print(f"   Campos: {list(campo_to_id.keys())[:5]}...")
    print()

    # 2. Cargar dataset
    print("📁 Cargando dataset...")
    dataset = LayoutLMv3Dataset.from_file(dataset_file)
    print(f"   Total samples: {len(dataset)}")
    print()

    # 3. Split train/val (80/20)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size

    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset,
        [train_size, val_size]
    )

    print(f"   Train: {len(train_dataset)} samples")
    print(f"   Val: {len(val_dataset)} samples")
    print()

    # 4. Cargar modelo
    print(f"🤖 Cargando modelo {model_name}...")

    model = LayoutLMv3ForTokenClassification.from_pretrained(
        model_name,
        num_labels=num_labels
    )

    # Mover a GPU si está disponible
    device = torch.device("cuda" if usar_gpu and torch.cuda.is_available() else "cpu")
    model.to(device)

    print(f"   Modelo cargado en: {device}")
    print()

    # 5. Configurar entrenamiento
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir=f"{output_dir}/logs",
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=3,
        push_to_hub=False,
        report_to="none"  # Cambiar a "tensorboard" si quieres logs
    )

    # 6. Crear Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )

    # 7. Entrenar
    print("🚀 Iniciando entrenamiento...")
    print()

    trainer.train()

    print()
    print("="*80)
    print("✅ ENTRENAMIENTO COMPLETADO")
    print("="*80)

    # 8. Evaluar
    print("\n📊 Evaluando modelo...")
    eval_results = trainer.evaluate()

    print(f"\n   Eval Loss: {eval_results['eval_loss']:.4f}")
    print()

    # 9. Guardar modelo final
    final_model_dir = Path(output_dir) / "modelo_final"
    model.save_pretrained(final_model_dir)

    # Guardar processor también
    processor = LayoutLMv3Processor.from_pretrained(model_name)
    processor.save_pretrained(final_model_dir)

    # Guardar label map
    with open(final_model_dir / "label_map.json", 'w') as f:
        json.dump({
            'campo_to_id': campo_to_id,
            'id_to_campo': {str(k): v for k, v in id_to_campo.items()}
        }, f, indent=2, ensure_ascii=False)

    print(f"💾 Modelo guardado en: {final_model_dir}")
    print()

    # 10. Resumen
    print("="*80)
    print("📋 RESUMEN")
    print("="*80)
    print(f"   Modelo entrenado: {model_name}")
    print(f"   Épocas completadas: {epochs}")
    print(f"   Eval loss final: {eval_results['eval_loss']:.4f}")
    print(f"   Número de campos: {num_labels}")
    print(f"   Modelo guardado: {final_model_dir}")
    print()
    print("🚀 El modelo está listo para usar!")
    print()


def main():
    """Función principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Entrena LayoutLMv3 para extracción de campos"
    )

    parser.add_argument(
        "--dataset-dir",
        required=True,
        help="Directorio con archivos *_avanzado.json"
    )

    parser.add_argument(
        "--images-dir",
        required=True,
        help="Directorio con imágenes de páginas PDF"
    )

    parser.add_argument(
        "--output-dir",
        default="modelo_entrenado",
        help="Directorio de salida (default: modelo_entrenado)"
    )

    parser.add_argument(
        "--model",
        default="microsoft/layoutlmv3-base",
        help="Modelo base (default: microsoft/layoutlmv3-base)"
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Número de épocas (default: 10)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Tamaño de batch (default: 4)"
    )

    parser.add_argument(
        "--lr",
        type=float,
        default=5e-5,
        help="Learning rate (default: 5e-5)"
    )

    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Forzar uso de CPU (no GPU)"
    )

    args = parser.parse_args()

    if not DEPS_OK:
        print("\n❌ Dependencias no disponibles")
        sys.exit(1)

    entrenar_modelo(
        dataset_dir=args.dataset_dir,
        images_dir=args.images_dir,
        output_dir=args.output_dir,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        usar_gpu=not args.cpu
    )


if __name__ == "__main__":
    main()
