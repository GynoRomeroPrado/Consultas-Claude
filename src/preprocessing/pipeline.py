"""
Pipeline Integrado de Preprocesamiento
Combina operaciones morfológicas y corrección de inclinación
para preparar facturas matriciales para procesamiento con Donut.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from .morphology import MorphologicalProcessor
from .deskewing import DeskewProcessor


class InvoicePreprocessingPipeline:
    """
    Pipeline completo de preprocesamiento para facturas peruanas con impresión matricial.

    Orden de operaciones:
    1. Corrección de inclinación (deskewing)
    2. Mejora de contraste
    3. Operaciones morfológicas para fusionar puntos matriciales
    4. Eliminación de ruido
    5. Redimensionamiento para el modelo
    """

    def __init__(
        self,
        target_size: Optional[Tuple[int, int]] = None,
        morphology_kernel: Tuple[int, int] = (3, 3),
        deskew_method: str = "projection",
        enhance_contrast: bool = True,
        remove_noise: bool = True
    ):
        """
        Args:
            target_size: Tamaño objetivo (ancho, alto) para redimensionar. None mantiene original
            morphology_kernel: Tamaño del kernel para operaciones morfológicas
            deskew_method: Método de deskewing ("projection" o "hough")
            enhance_contrast: Si aplicar mejora de contraste CLAHE
            remove_noise: Si eliminar ruido pequeño
        """
        self.target_size = target_size
        self.deskew_method = deskew_method
        self.enhance_contrast_flag = enhance_contrast
        self.remove_noise_flag = remove_noise

        # Inicializar procesadores
        self.morph_processor = MorphologicalProcessor(
            kernel_size=morphology_kernel,
            apply_blur=True
        )
        self.deskew_processor = DeskewProcessor()

    def process(
        self,
        image: np.ndarray,
        return_metadata: bool = False
    ) -> np.ndarray | Tuple[np.ndarray, Dict[str, Any]]:
        """
        Procesa una imagen de factura a través del pipeline completo.

        Args:
            image: Imagen de entrada (BGR o escala de grises)
            return_metadata: Si devolver metadatos del procesamiento

        Returns:
            Imagen procesada, o tupla (imagen, metadata) si return_metadata=True
        """
        metadata = {
            "original_shape": image.shape,
            "skew_angle": 0.0,
            "operations_applied": []
        }

        # Paso 1: Corrección de inclinación
        deskewed, angle = self.deskew_processor.deskew(
            image,
            method=self.deskew_method
        )
        metadata["skew_angle"] = angle
        metadata["operations_applied"].append("deskewing")
        current = deskewed

        # Paso 2: Mejorar contraste (especialmente útil para papel químico desvanecido)
        if self.enhance_contrast_flag:
            if len(current.shape) == 3:
                gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
            else:
                gray = current.copy()

            enhanced = self.morph_processor.enhance_contrast(gray)
            current = enhanced
            metadata["operations_applied"].append("contrast_enhancement")
        else:
            # Convertir a escala de grises
            if len(current.shape) == 3:
                current = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)

        # Paso 3: Operaciones morfológicas para fusionar puntos matriciales
        morphed = self.morph_processor.enhance_dot_matrix(current)
        current = morphed
        metadata["operations_applied"].append("morphological_closing")

        # Paso 4: Eliminar ruido
        if self.remove_noise_flag:
            # Invertir para que el texto sea blanco sobre negro
            inverted = cv2.bitwise_not(current)
            denoised = self.morph_processor.remove_noise(inverted, min_area=5)
            # Volver a invertir
            current = cv2.bitwise_not(denoised)
            metadata["operations_applied"].append("noise_removal")

        # Paso 5: Redimensionar si se especifica tamaño objetivo
        if self.target_size is not None:
            resized = cv2.resize(
                current,
                self.target_size,
                interpolation=cv2.INTER_CUBIC
            )
            current = resized
            metadata["operations_applied"].append("resize")
            metadata["final_shape"] = current.shape

        # Convertir de vuelta a RGB para el modelo (Donut espera RGB)
        final = cv2.cvtColor(current, cv2.COLOR_GRAY2RGB)
        metadata["final_shape"] = final.shape

        if return_metadata:
            return final, metadata
        return final

    def process_batch(
        self,
        images: list,
        show_progress: bool = True
    ) -> list:
        """
        Procesa un lote de imágenes.

        Args:
            images: Lista de imágenes numpy
            show_progress: Si mostrar barra de progreso

        Returns:
            Lista de imágenes procesadas
        """
        processed = []

        iterator = images
        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(images, desc="Preprocessing")
            except ImportError:
                pass

        for img in iterator:
            processed_img = self.process(img)
            processed.append(processed_img)

        return processed

    def process_directory(
        self,
        input_dir: str,
        output_dir: str,
        file_pattern: str = "*.png",
        save_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Procesa todas las imágenes en un directorio.

        Args:
            input_dir: Directorio de entrada
            output_dir: Directorio de salida
            file_pattern: Patrón de archivos a procesar
            save_metadata: Si guardar metadata en JSON

        Returns:
            Diccionario con estadísticas del procesamiento
        """
        import json
        from tqdm import tqdm

        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Obtener archivos
        image_files = list(input_path.glob(file_pattern))

        stats = {
            "total_files": len(image_files),
            "processed": 0,
            "failed": 0,
            "average_skew_angle": 0.0,
            "failed_files": []
        }

        total_angle = 0.0

        for img_file in tqdm(image_files, desc="Processing directory"):
            try:
                # Leer imagen
                image = cv2.imread(str(img_file))
                if image is None:
                    raise ValueError(f"Could not read {img_file}")

                # Procesar
                processed, metadata = self.process(image, return_metadata=True)

                # Guardar
                output_file = output_path / img_file.name
                cv2.imwrite(str(output_file), processed)

                # Guardar metadata si se solicita
                if save_metadata:
                    metadata_file = output_path / f"{img_file.stem}_metadata.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)

                stats["processed"] += 1
                total_angle += abs(metadata["skew_angle"])

            except Exception as e:
                stats["failed"] += 1
                stats["failed_files"].append({
                    "file": str(img_file),
                    "error": str(e)
                })

        # Calcular estadísticas finales
        if stats["processed"] > 0:
            stats["average_skew_angle"] = total_angle / stats["processed"]

        return stats


def create_high_resolution_pipeline(
    target_width: int = 1920,
    target_height: int = 2560
) -> InvoicePreprocessingPipeline:
    """
    Crea un pipeline configurado para alta resolución (necesario para Donut).

    Args:
        target_width: Ancho objetivo en píxeles
        target_height: Alto objetivo en píxeles

    Returns:
        Pipeline configurado para alta resolución
    """
    return InvoicePreprocessingPipeline(
        target_size=(target_width, target_height),
        morphology_kernel=(3, 3),
        deskew_method="projection",
        enhance_contrast=True,
        remove_noise=True
    )


def preprocess_for_donut(
    image_path: str,
    output_path: Optional[str] = None
) -> np.ndarray:
    """
    Función de conveniencia para preprocesar una factura para Donut.

    Args:
        image_path: Ruta a la imagen de entrada
        output_path: Ruta opcional para guardar el resultado

    Returns:
        Imagen preprocesada lista para Donut
    """
    # Leer imagen
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")

    # Crear pipeline de alta resolución
    pipeline = create_high_resolution_pipeline()

    # Procesar
    processed = pipeline.process(image)

    # Guardar si se especifica ruta
    if output_path:
        cv2.imwrite(output_path, processed)

    return processed
