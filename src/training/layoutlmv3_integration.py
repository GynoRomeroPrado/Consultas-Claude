"""
Integración directa con LayoutLMv3 de Hugging Face Transformers.

Convierte el dataset generado al formato exacto requerido por LayoutLMv3Processor
y proporciona utilidades para entrenamiento.
"""

import json
import torch
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)

try:
    from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
    from torch.utils.data import Dataset, DataLoader
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "Transformers no está instalado. "
        "Instala con: pip install transformers torch"
    )


class LayoutLMv3DatasetConverter:
    """
    Convierte dataset generado al formato LayoutLMv3.

    El dataset debe estar en formato generado por generar_dataset_avanzado.py
    con coordenadas normalizadas 0-1000.
    """

    def __init__(
        self,
        model_name: str = "microsoft/layoutlmv3-base",
        max_length: int = 512
    ):
        """
        Inicializa conversor.

        Args:
            model_name: Nombre del modelo LayoutLMv3 pre-entrenado
            max_length: Longitud máxima de secuencia (tokens)
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Transformers es requerido. "
                "Instala con: pip install transformers torch"
            )

        self.model_name = model_name
        self.max_length = max_length
        self.processor = None
        self._load_processor()

    def _load_processor(self):
        """Carga LayoutLMv3Processor."""
        try:
            self.processor = LayoutLMv3Processor.from_pretrained(
                self.model_name,
                apply_ocr=False  # Ya tenemos coordenadas
            )
            logger.info(f"Processor cargado: {self.model_name}")
        except Exception as e:
            logger.error(f"Error cargando processor: {e}")
            raise

    def convert_sample(
        self,
        coordenadas_json: Dict[str, Any],
        image_path: str,
        label_map: Optional[Dict[str, int]] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Convierte un sample individual al formato LayoutLMv3.

        Args:
            coordenadas_json: Dict con coordenadas (formato generado por scripts)
            image_path: Ruta a la imagen de la página PDF
            label_map: Mapeo de campo → label_id (para token classification)

        Returns:
            Dict con tensores listos para LayoutLMv3:
            {
                'input_ids': tensor,
                'attention_mask': tensor,
                'bbox': tensor,
                'pixel_values': tensor,
                'labels': tensor (si label_map provided)
            }
        """
        # 1. Cargar imagen
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            logger.error(f"Error cargando imagen {image_path}: {e}")
            raise

        # 2. Extraer palabras y bboxes
        words = []
        boxes = []

        for coord in coordenadas_json.get('coordenadas', []):
            words.append(coord['texto'])
            boxes.append(coord['bbox_normalizada'])  # Ya en escala 0-1000

        if not words:
            raise ValueError("No hay palabras en el sample")

        # 3. Procesar con LayoutLMv3Processor
        encoding = self.processor(
            image,
            words,
            boxes=boxes,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt"
        )

        # 4. Agregar labels si se proporciona label_map
        if label_map is not None:
            labels = []
            for coord in coordenadas_json.get('coordenadas', []):
                campo = coord['campo']
                label_id = label_map.get(campo, 0)  # 0 = "O" (outside)
                labels.append(label_id)

            # Padding de labels
            labels += [0] * (self.max_length - len(labels))
            labels = labels[:self.max_length]

            encoding['labels'] = torch.tensor(labels, dtype=torch.long).unsqueeze(0)

        return {k: v.squeeze(0) for k, v in encoding.items()}

    def convert_dataset(
        self,
        dataset_dir: str,
        images_dir: str,
        output_file: str,
        label_map: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Convierte dataset completo al formato LayoutLMv3.

        Args:
            dataset_dir: Directorio con archivos *_avanzado.json
            images_dir: Directorio con imágenes de páginas PDF
            output_file: Archivo donde guardar dataset procesado
            label_map: Mapeo de campos a IDs de labels

        Returns:
            Lista de samples procesados
        """
        dataset_path = Path(dataset_dir)
        images_path = Path(images_dir)

        # Buscar archivos de coordenadas
        coord_files = list(dataset_path.glob("*_avanzado.json"))

        if not coord_files:
            raise ValueError(f"No se encontraron archivos en {dataset_dir}")

        logger.info(f"Encontrados {len(coord_files)} archivos")

        processed_samples = []

        for coord_file in coord_files:
            try:
                with open(coord_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Construir ruta a imagen
                # Asume que las imágenes tienen el mismo nombre que el JSON
                doc_id = data['documento_id']
                image_file = images_path / f"{doc_id}.png"

                if not image_file.exists():
                    logger.warning(f"Imagen no encontrada: {image_file}")
                    continue

                # Convertir sample
                encoding = self.convert_sample(data, str(image_file), label_map)

                processed_samples.append({
                    'documento_id': doc_id,
                    'encoding': encoding,
                    'metadata': {
                        'pagina': data.get('pagina', 0),
                        'total_campos': data.get('total_campos', 0),
                        'confianza_promedio': data.get('confianza_promedio', 0)
                    }
                })

                logger.debug(f"Procesado: {doc_id}")

            except Exception as e:
                logger.error(f"Error procesando {coord_file.name}: {e}")
                continue

        # Guardar dataset procesado
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        torch.save(processed_samples, output_path)

        logger.info(f"Dataset guardado: {output_path} ({len(processed_samples)} samples)")

        return processed_samples

    def create_label_map(
        self,
        dataset_dir: str
    ) -> Tuple[Dict[str, int], Dict[int, str]]:
        """
        Crea mapeo de campos a IDs de labels automáticamente.

        Args:
            dataset_dir: Directorio con archivos de coordenadas

        Returns:
            Tupla (campo→id, id→campo)
        """
        dataset_path = Path(dataset_dir)
        coord_files = list(dataset_path.glob("*_avanzado.json"))

        # Recolectar todos los campos únicos
        campos_unicos = set()

        for coord_file in coord_files:
            try:
                with open(coord_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for coord in data.get('coordenadas', []):
                    campos_unicos.add(coord['campo'])

            except Exception as e:
                logger.error(f"Error leyendo {coord_file.name}: {e}")
                continue

        # Crear mapeo
        # 0 = "O" (outside/ningún campo)
        # 1+ = campos específicos
        campo_to_id = {"O": 0}
        id_to_campo = {0: "O"}

        for idx, campo in enumerate(sorted(campos_unicos), start=1):
            campo_to_id[campo] = idx
            id_to_campo[idx] = campo

        logger.info(f"Label map creado: {len(campo_to_id)} campos")

        return campo_to_id, id_to_campo


class LayoutLMv3Dataset(Dataset):
    """
    PyTorch Dataset para LayoutLMv3.

    Carga samples pre-procesados y los prepara para entrenamiento.
    """

    def __init__(self, processed_samples: List[Dict[str, Any]]):
        """
        Inicializa dataset.

        Args:
            processed_samples: Lista de samples procesados
        """
        self.samples = processed_samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        Obtiene un sample.

        Returns:
            Dict con tensores listos para el modelo
        """
        return self.samples[idx]['encoding']

    @classmethod
    def from_file(cls, dataset_file: str) -> 'LayoutLMv3Dataset':
        """
        Carga dataset desde archivo.

        Args:
            dataset_file: Ruta al archivo .pt generado

        Returns:
            Instance de LayoutLMv3Dataset
        """
        samples = torch.load(dataset_file)
        return cls(samples)


def create_dataloader(
    dataset: LayoutLMv3Dataset,
    batch_size: int = 4,
    shuffle: bool = True,
    num_workers: int = 0
) -> DataLoader:
    """
    Crea DataLoader para entrenamiento.

    Args:
        dataset: LayoutLMv3Dataset
        batch_size: Tamaño de batch
        shuffle: Si mezclar samples
        num_workers: Número de workers para carga paralela

    Returns:
        PyTorch DataLoader
    """
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )


def prepare_for_training(
    dataset_dir: str,
    images_dir: str,
    output_dir: str,
    model_name: str = "microsoft/layoutlmv3-base",
    max_length: int = 512
) -> Tuple[str, Dict[str, int], Dict[int, str]]:
    """
    Función de conveniencia para preparar dataset completo.

    Args:
        dataset_dir: Directorio con coordenadas
        images_dir: Directorio con imágenes
        output_dir: Directorio de salida
        model_name: Modelo LayoutLMv3 a usar
        max_length: Longitud máxima de secuencia

    Returns:
        Tupla (ruta_dataset_procesado, campo_to_id, id_to_campo)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Crear conversor
    converter = LayoutLMv3DatasetConverter(model_name, max_length)

    # 2. Crear label map
    campo_to_id, id_to_campo = converter.create_label_map(dataset_dir)

    # Guardar label map
    label_map_file = output_path / "label_map.json"
    with open(label_map_file, 'w', encoding='utf-8') as f:
        json.dump({
            'campo_to_id': campo_to_id,
            'id_to_campo': {str(k): v for k, v in id_to_campo.items()}
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"Label map guardado: {label_map_file}")

    # 3. Convertir dataset
    dataset_file = output_path / "layoutlmv3_dataset.pt"

    converter.convert_dataset(
        dataset_dir,
        images_dir,
        str(dataset_file),
        label_map=campo_to_id
    )

    logger.info(f"Dataset listo para entrenamiento: {dataset_file}")

    return str(dataset_file), campo_to_id, id_to_campo
