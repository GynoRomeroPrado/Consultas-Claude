"""
Configuración del Modelo Donut para Facturas Peruanas
Configuración optimizada para alta resolución (1920x2560) y procesamiento
de facturas con impresión matricial.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class DonutModelConfig:
    """
    Configuración para el modelo Donut especializado en facturas peruanas.
    """

    # Modelo base
    model_name: str = "naver-clova-ix/donut-base"

    # Configuración de imagen de alta resolución
    image_size: List[int] = field(default_factory=lambda: [2560, 1920])  # [height, width]
    align_long_axis: bool = True

    # Configuración del encoder (Swin Transformer)
    encoder_hidden_size: int = 768
    encoder_num_layers: int = 12
    encoder_num_heads: int = 12
    window_size: int = 7
    patch_size: int = 4

    # Configuración del decoder (BART)
    decoder_hidden_size: int = 1024
    decoder_num_layers: int = 4
    decoder_num_heads: int = 16
    max_length: int = 768  # Longitud máxima de secuencia de salida

    # Vocabulario y tokens especiales
    vocab_size: int = 50265
    pad_token_id: int = 1
    bos_token_id: int = 0
    eos_token_id: int = 2

    # Interpolación de embeddings posicionales
    # CRÍTICO: Permite usar pesos pre-entrenados con nueva resolución
    interpolate_position_embeddings: bool = True
    position_embedding_type: str = "bicubic"  # bicubic o bilinear

    # Esquema JSON de salida optimizado (claves cortas para ahorrar tokens)
    task_start_token: str = "<s_invoice>"
    task_end_token: str = "</s_invoice>"

    # Campos de factura peruana (usando claves cortas)
    output_schema: Dict[str, Any] = field(default_factory=lambda: {
        "ruc_emisor": "ruc_e",           # RUC del emisor
        "razon_social": "rs",             # Razón social
        "ruc_receptor": "ruc_r",          # RUC del receptor
        "fecha_emision": "fec",           # Fecha de emisión
        "numero_factura": "num",          # Número de factura
        "serie": "ser",                   # Serie
        "subtotal": "sub",                # Subtotal
        "igv": "igv",                     # IGV (18%)
        "total": "tot",                   # Total
        "items": [                        # Líneas de productos/servicios
            {
                "descripcion": "d",       # Descripción
                "cantidad": "q",          # Cantidad
                "precio_unitario": "pu",  # Precio unitario
                "valor_total": "vt"       # Valor total
            }
        ]
    })

    # Dropout para regularización
    dropout: float = 0.1
    attention_dropout: float = 0.1

    def to_transformers_config(self) -> Dict[str, Any]:
        """
        Convierte esta configuración al formato de HuggingFace Transformers.

        Returns:
            Diccionario con configuración compatible
        """
        return {
            "image_size": self.image_size,
            "align_long_axis": self.align_long_axis,
            "encoder": {
                "hidden_size": self.encoder_hidden_size,
                "num_hidden_layers": self.encoder_num_layers,
                "num_attention_heads": self.encoder_num_heads,
                "window_size": self.window_size,
                "patch_size": self.patch_size,
            },
            "decoder": {
                "hidden_size": self.decoder_hidden_size,
                "num_hidden_layers": self.decoder_num_layers,
                "num_attention_heads": self.decoder_num_heads,
                "max_length": self.max_length,
            },
            "vocab_size": self.vocab_size,
            "pad_token_id": self.pad_token_id,
            "bos_token_id": self.bos_token_id,
            "eos_token_id": self.eos_token_id,
            "dropout": self.dropout,
            "attention_dropout": self.attention_dropout,
        }


@dataclass
class TrainingConfig:
    """
    Configuración para el entrenamiento del modelo.
    """

    # Directorios
    data_dir: str = "./data"
    output_dir: str = "./checkpoints"
    logging_dir: str = "./logs"

    # Dataset
    train_split: float = 0.85
    val_split: float = 0.15

    # Entrenamiento
    num_epochs: int = 30
    batch_size: int = 2  # Pequeño debido a la alta resolución
    gradient_accumulation_steps: int = 8  # Batch efectivo = 16
    learning_rate: float = 3e-5
    warmup_steps: int = 500
    weight_decay: float = 0.01

    # Optimización
    fp16: bool = True  # Precisión mixta para ahorrar memoria
    gradient_checkpointing: bool = True  # Ahorrar memoria
    dataloader_num_workers: int = 4

    # Evaluación
    eval_steps: int = 500
    save_steps: int = 1000
    save_total_limit: int = 3

    # Early stopping
    early_stopping_patience: int = 5
    early_stopping_threshold: float = 0.001

    # Logging
    logging_steps: int = 100
    report_to: List[str] = field(default_factory=lambda: ["tensorboard"])

    # Estrategia de entrenamiento multi-fase
    phase1_synthetic_only: bool = True
    phase1_epochs: int = 15
    phase2_mixed_data: bool = True
    phase2_epochs: int = 10
    phase3_real_only: bool = True
    phase3_epochs: int = 5

    def get_phase_config(self, phase: int) -> Dict[str, Any]:
        """
        Obtiene configuración específica para cada fase de entrenamiento.

        Args:
            phase: Número de fase (1, 2, o 3)

        Returns:
            Configuración de la fase
        """
        configs = {
            1: {
                "name": "Synthetic Data Training",
                "epochs": self.phase1_epochs,
                "use_synthetic": True,
                "use_real": False,
                "learning_rate": self.learning_rate,
                "description": "Entrenamiento inicial con datos sintéticos/augmentados"
            },
            2: {
                "name": "Mixed Data Fine-tuning",
                "epochs": self.phase2_epochs,
                "use_synthetic": True,
                "use_real": True,
                "learning_rate": self.learning_rate * 0.5,
                "description": "Ajuste con datos sintéticos y reales mezclados"
            },
            3: {
                "name": "Real Data Final Tuning",
                "epochs": self.phase3_epochs,
                "use_synthetic": False,
                "use_real": True,
                "learning_rate": self.learning_rate * 0.1,
                "description": "Ajuste fino final solo con datos reales"
            }
        }
        return configs.get(phase, configs[1])


@dataclass
class InferenceConfig:
    """
    Configuración para inferencia.
    """

    model_path: str = "./checkpoints/best_model"
    device: str = "cuda"  # "cuda" o "cpu"

    # Generación
    max_length: int = 768
    num_beams: int = 1  # Beam search
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95
    repetition_penalty: float = 1.2

    # Post-procesamiento
    validate_ruc: bool = True  # Validar RUCs con lógica SUNAT
    validate_totals: bool = True  # Validar que subtotal + IGV = total
    format_dates: bool = True  # Formatear fechas

    # Batch inference
    batch_size: int = 4
    num_workers: int = 2


def create_default_model_config() -> DonutModelConfig:
    """
    Crea configuración por defecto del modelo.

    Returns:
        Configuración del modelo
    """
    return DonutModelConfig()


def create_high_resolution_config(
    width: int = 1920,
    height: int = 2560
) -> DonutModelConfig:
    """
    Crea configuración para alta resolución.

    Args:
        width: Ancho de imagen
        height: Alto de imagen

    Returns:
        Configuración optimizada para alta resolución
    """
    config = DonutModelConfig()
    config.image_size = [height, width]
    config.interpolate_position_embeddings = True
    config.position_embedding_type = "bicubic"
    return config


def create_training_config(
    output_dir: str = "./checkpoints",
    num_epochs: int = 30,
    batch_size: int = 2
) -> TrainingConfig:
    """
    Crea configuración de entrenamiento.

    Args:
        output_dir: Directorio de salida
        num_epochs: Número de epochs
        batch_size: Tamaño de batch

    Returns:
        Configuración de entrenamiento
    """
    return TrainingConfig(
        output_dir=output_dir,
        num_epochs=num_epochs,
        batch_size=batch_size
    )


def load_config_from_yaml(config_path: str) -> Dict[str, Any]:
    """
    Carga configuración desde archivo YAML.

    Args:
        config_path: Ruta al archivo YAML

    Returns:
        Configuración cargada
    """
    import yaml

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def save_config_to_yaml(config: Any, output_path: str):
    """
    Guarda configuración a archivo YAML.

    Args:
        config: Configuración a guardar
        output_path: Ruta de salida
    """
    import yaml
    from dataclasses import asdict

    config_dict = asdict(config) if hasattr(config, '__dataclass_fields__') else config

    with open(output_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
