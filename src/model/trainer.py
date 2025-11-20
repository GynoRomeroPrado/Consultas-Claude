"""
Módulo de Entrenamiento para Donut
Implementa entrenamiento estratégico multi-fase:
1. Fase 1: Datos sintéticos/augmentados
2. Fase 2: Datos mixtos
3. Fase 3: Datos reales (fine-tuning final)
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import (
    VisionEncoderDecoderModel,
    DonutProcessor,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback
)
from typing import Optional, Dict, Any, List
import json
from pathlib import Path
from tqdm import tqdm
import numpy as np


class DonutTrainer:
    """
    Trainer especializado para facturas peruanas con estrategia multi-fase.
    """

    def __init__(
        self,
        model_config,
        training_config,
        processor: Optional[DonutProcessor] = None
    ):
        """
        Args:
            model_config: Configuración del modelo (DonutModelConfig)
            training_config: Configuración de entrenamiento (TrainingConfig)
            processor: Procesador Donut pre-configurado (opcional)
        """
        self.model_config = model_config
        self.training_config = training_config
        self.processor = processor
        self.model = None

        # Configurar device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

    def initialize_model(self, from_pretrained: bool = True):
        """
        Inicializa el modelo Donut.

        Args:
            from_pretrained: Si cargar pesos pre-entrenados
        """
        if from_pretrained:
            print(f"Loading pretrained model: {self.model_config.model_name}")
            self.model = VisionEncoderDecoderModel.from_pretrained(
                self.model_config.model_name
            )

            # Ajustar para alta resolución
            self._configure_high_resolution()

        else:
            # Crear modelo desde cero (no recomendado)
            from transformers import VisionEncoderDecoderConfig
            config = VisionEncoderDecoderConfig.from_pretrained(
                self.model_config.model_name
            )
            self.model = VisionEncoderDecoderModel(config)

        # Configurar decoder
        self.model.config.decoder_start_token_id = self.model_config.bos_token_id
        self.model.config.pad_token_id = self.model_config.pad_token_id
        self.model.config.eos_token_id = self.model_config.eos_token_id

        # Gradient checkpointing para ahorrar memoria
        if self.training_config.gradient_checkpointing:
            self.model.encoder.gradient_checkpointing_enable()

        self.model.to(self.device)
        print(f"Model initialized on {self.device}")

    def _configure_high_resolution(self):
        """
        Configura el modelo para alta resolución con interpolación de embeddings.
        """
        target_size = tuple(self.model_config.image_size)
        current_size = self.model.encoder.config.image_size

        if target_size != current_size:
            print(f"Adjusting image size from {current_size} to {target_size}")

            # Actualizar config
            self.model.encoder.config.image_size = target_size

            # Interpolar embeddings posicionales
            if self.model_config.interpolate_position_embeddings:
                self._interpolate_position_embeddings(
                    current_size,
                    target_size
                )

    def _interpolate_position_embeddings(
        self,
        old_size: int,
        new_size: tuple
    ):
        """
        Interpola embeddings posicionales para nueva resolución.

        Args:
            old_size: Tamaño original
            new_size: Nuevo tamaño (height, width)
        """
        import torch.nn.functional as F

        # Obtener embeddings posicionales actuales
        pos_embed = self.model.encoder.embeddings.position_embeddings

        # Calcular grid viejo y nuevo
        old_h = old_w = old_size // self.model_config.patch_size
        new_h, new_w = [s // self.model_config.patch_size for s in new_size]

        # Reshape embeddings
        pos_embed = pos_embed.reshape(1, old_h, old_w, -1).permute(0, 3, 1, 2)

        # Interpolar usando bicubic
        new_pos_embed = F.interpolate(
            pos_embed,
            size=(new_h, new_w),
            mode=self.model_config.position_embedding_type,
            align_corners=False
        )

        # Reshape de vuelta
        new_pos_embed = new_pos_embed.permute(0, 2, 3, 1).reshape(1, new_h * new_w, -1)

        # Actualizar embeddings
        self.model.encoder.embeddings.position_embeddings = nn.Parameter(
            new_pos_embed.squeeze(0)
        )

        print(f"Position embeddings interpolated: ({old_h}x{old_w}) -> ({new_h}x{new_w})")

    def train_phase(
        self,
        phase_num: int,
        train_dataset: Dataset,
        val_dataset: Optional[Dataset] = None
    ) -> Dict[str, Any]:
        """
        Entrena una fase específica.

        Args:
            phase_num: Número de fase (1, 2, o 3)
            train_dataset: Dataset de entrenamiento
            val_dataset: Dataset de validación

        Returns:
            Métricas de entrenamiento
        """
        phase_config = self.training_config.get_phase_config(phase_num)
        print(f"\n{'='*60}")
        print(f"Phase {phase_num}: {phase_config['name']}")
        print(f"Description: {phase_config['description']}")
        print(f"Epochs: {phase_config['epochs']}")
        print(f"Learning Rate: {phase_config['learning_rate']}")
        print(f"{'='*60}\n")

        # Configurar argumentos de entrenamiento
        training_args = TrainingArguments(
            output_dir=f"{self.training_config.output_dir}/phase_{phase_num}",
            num_train_epochs=phase_config['epochs'],
            per_device_train_batch_size=self.training_config.batch_size,
            per_device_eval_batch_size=self.training_config.batch_size,
            gradient_accumulation_steps=self.training_config.gradient_accumulation_steps,
            learning_rate=phase_config['learning_rate'],
            warmup_steps=self.training_config.warmup_steps,
            weight_decay=self.training_config.weight_decay,
            fp16=self.training_config.fp16,
            logging_dir=f"{self.training_config.logging_dir}/phase_{phase_num}",
            logging_steps=self.training_config.logging_steps,
            eval_steps=self.training_config.eval_steps,
            save_steps=self.training_config.save_steps,
            save_total_limit=self.training_config.save_total_limit,
            evaluation_strategy="steps" if val_dataset else "no",
            load_best_model_at_end=True if val_dataset else False,
            metric_for_best_model="eval_loss" if val_dataset else None,
            greater_is_better=False,
            report_to=self.training_config.report_to,
            dataloader_num_workers=self.training_config.dataloader_num_workers,
        )

        # Crear trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            callbacks=[
                EarlyStoppingCallback(
                    early_stopping_patience=self.training_config.early_stopping_patience,
                    early_stopping_threshold=self.training_config.early_stopping_threshold
                )
            ] if val_dataset else []
        )

        # Entrenar
        train_result = trainer.train()

        # Guardar modelo de la fase
        phase_model_path = f"{self.training_config.output_dir}/phase_{phase_num}_final"
        trainer.save_model(phase_model_path)
        print(f"Phase {phase_num} model saved to {phase_model_path}")

        return train_result.metrics

    def train_all_phases(
        self,
        synthetic_dataset: Dataset,
        real_dataset: Dataset,
        val_dataset: Optional[Dataset] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento multi-fase completo.

        Args:
            synthetic_dataset: Dataset con imágenes sintéticas/augmentadas
            real_dataset: Dataset con imágenes reales
            val_dataset: Dataset de validación

        Returns:
            Métricas de todas las fases
        """
        all_metrics = {}

        # Fase 1: Solo sintéticos
        if self.training_config.phase1_synthetic_only:
            metrics_1 = self.train_phase(1, synthetic_dataset, val_dataset)
            all_metrics['phase_1'] = metrics_1

        # Fase 2: Datos mixtos
        if self.training_config.phase2_mixed_data:
            from torch.utils.data import ConcatDataset
            mixed_dataset = ConcatDataset([synthetic_dataset, real_dataset])
            metrics_2 = self.train_phase(2, mixed_dataset, val_dataset)
            all_metrics['phase_2'] = metrics_2

        # Fase 3: Solo reales (fine-tuning final)
        if self.training_config.phase3_real_only:
            metrics_3 = self.train_phase(3, real_dataset, val_dataset)
            all_metrics['phase_3'] = metrics_3

        # Guardar modelo final
        final_model_path = f"{self.training_config.output_dir}/final_model"
        self.model.save_pretrained(final_model_path)
        if self.processor:
            self.processor.save_pretrained(final_model_path)
        print(f"\nFinal model saved to {final_model_path}")

        return all_metrics

    def evaluate(self, eval_dataset: Dataset) -> Dict[str, float]:
        """
        Evalúa el modelo en un dataset.

        Args:
            eval_dataset: Dataset de evaluación

        Returns:
            Métricas de evaluación
        """
        self.model.eval()
        total_loss = 0.0
        num_batches = 0

        dataloader = DataLoader(
            eval_dataset,
            batch_size=self.training_config.batch_size,
            shuffle=False
        )

        with torch.no_grad():
            for batch in tqdm(dataloader, desc="Evaluating"):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = self.model(**batch)
                total_loss += outputs.loss.item()
                num_batches += 1

        avg_loss = total_loss / num_batches
        return {"eval_loss": avg_loss}

    def save_checkpoint(self, checkpoint_path: str):
        """
        Guarda checkpoint del modelo.

        Args:
            checkpoint_path: Ruta donde guardar
        """
        checkpoint_path = Path(checkpoint_path)
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(str(checkpoint_path))
        if self.processor:
            self.processor.save_pretrained(str(checkpoint_path))

        print(f"Checkpoint saved to {checkpoint_path}")

    def load_checkpoint(self, checkpoint_path: str):
        """
        Carga checkpoint del modelo.

        Args:
            checkpoint_path: Ruta del checkpoint
        """
        print(f"Loading checkpoint from {checkpoint_path}")
        self.model = VisionEncoderDecoderModel.from_pretrained(checkpoint_path)
        self.model.to(self.device)

        if Path(checkpoint_path).joinpath("preprocessor_config.json").exists():
            self.processor = DonutProcessor.from_pretrained(checkpoint_path)

        print("Checkpoint loaded successfully")


def create_trainer(
    model_config,
    training_config,
    processor: Optional[DonutProcessor] = None
) -> DonutTrainer:
    """
    Crea un trainer configurado.

    Args:
        model_config: Configuración del modelo
        training_config: Configuración de entrenamiento
        processor: Procesador opcional

    Returns:
        Trainer inicializado
    """
    trainer = DonutTrainer(model_config, training_config, processor)
    trainer.initialize_model(from_pretrained=True)
    return trainer
