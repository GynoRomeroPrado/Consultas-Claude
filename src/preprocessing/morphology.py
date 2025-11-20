"""
Módulo de Operaciones Morfológicas para Impresiones Matriciales
Implementa operaciones de cierre morfológico (A ⊕ B) ⊖ B para fusionar
puntos dispersos de impresoras matriciales en glifos sólidos legibles.
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class MorphologicalProcessor:
    """
    Procesador morfológico especializado para facturas con impresión matricial.
    Convierte patrones de puntos en texto sólido legible.
    """

    def __init__(
        self,
        kernel_size: Tuple[int, int] = (3, 3),
        iterations: int = 1,
        gaussian_blur_size: Tuple[int, int] = (3, 3),
        apply_blur: bool = True
    ):
        """
        Args:
            kernel_size: Tamaño del kernel rectangular para morfología (ancho, alto)
            iterations: Número de iteraciones de cierre morfológico
            gaussian_blur_size: Tamaño del kernel para desenfoque gaussiano
            apply_blur: Si aplicar desenfoque gaussiano suave post-morfología
        """
        self.kernel_size = kernel_size
        self.iterations = iterations
        self.gaussian_blur_size = gaussian_blur_size
        self.apply_blur = apply_blur

        # Crear kernel rectangular para cierre morfológico
        self.kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            self.kernel_size
        )

    def closing_operation(self, image: np.ndarray) -> np.ndarray:
        """
        Aplica operación de cierre morfológico: (A ⊕ B) ⊖ B
        Dilatación seguida de erosión para cerrar gaps pequeños.

        Args:
            image: Imagen en escala de grises (numpy array)

        Returns:
            Imagen procesada con puntos fusionados
        """
        closed = cv2.morphologyEx(
            image,
            cv2.MORPH_CLOSE,
            self.kernel,
            iterations=self.iterations
        )
        return closed

    def enhance_dot_matrix(self, image: np.ndarray) -> np.ndarray:
        """
        Pipeline completo para mejorar impresiones matriciales.

        Args:
            image: Imagen BGR o escala de grises

        Returns:
            Imagen mejorada lista para el modelo
        """
        # Convertir a escala de grises si es necesario
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Binarización adaptativa para separar texto del fondo
        # Útil cuando hay variaciones de iluminación
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )

        # Aplicar cierre morfológico para fusionar puntos
        closed = self.closing_operation(binary)

        # Opcional: Desenfoque gaussiano suave para eliminar ruido residual
        if self.apply_blur:
            blurred = cv2.GaussianBlur(
                closed,
                self.gaussian_blur_size,
                sigmaX=0
            )
            return blurred

        return closed

    def process_with_multiple_kernels(
        self,
        image: np.ndarray,
        kernel_sizes: list = [(2, 2), (3, 3), (4, 2)]
    ) -> np.ndarray:
        """
        Aplica múltiples operaciones morfológicas con diferentes kernels
        y combina los resultados para mejor robustez.

        Args:
            image: Imagen de entrada
            kernel_sizes: Lista de tamaños de kernel a probar

        Returns:
            Imagen combinada optimizada
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        results = []

        for ksize in kernel_sizes:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, ksize)
            closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            results.append(closed)

        # Combinar resultados usando promedio ponderado
        # Dar más peso a kernels medianos
        weights = [0.3, 0.5, 0.2] if len(results) == 3 else [1.0/len(results)] * len(results)
        combined = np.zeros_like(gray, dtype=np.float32)

        for result, weight in zip(results, weights):
            combined += result.astype(np.float32) * weight

        return combined.astype(np.uint8)

    def remove_noise(self, image: np.ndarray, min_area: int = 5) -> np.ndarray:
        """
        Elimina componentes conectados pequeños (ruido).

        Args:
            image: Imagen binaria
            min_area: Área mínima en píxeles para conservar un componente

        Returns:
            Imagen sin ruido pequeño
        """
        # Encontrar componentes conectados
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            image,
            connectivity=8
        )

        # Crear máscara para componentes válidos
        mask = np.zeros_like(image)

        for i in range(1, num_labels):  # Saltar el fondo (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_area:
                mask[labels == i] = 255

        return mask

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Mejora el contraste usando CLAHE (Contrast Limited Adaptive Histogram Equalization).
        Útil para facturas con papel químico desvanecido.

        Args:
            image: Imagen en escala de grises

        Returns:
            Imagen con contraste mejorado
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced


def preprocess_invoice_image(
    image_path: str,
    output_path: Optional[str] = None,
    kernel_size: Tuple[int, int] = (3, 3)
) -> np.ndarray:
    """
    Función de conveniencia para preprocesar una imagen de factura.

    Args:
        image_path: Ruta a la imagen de entrada
        output_path: Ruta opcional para guardar el resultado
        kernel_size: Tamaño del kernel morfológico

    Returns:
        Imagen preprocesada
    """
    # Leer imagen
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")

    # Procesar
    processor = MorphologicalProcessor(kernel_size=kernel_size)
    processed = processor.enhance_dot_matrix(image)

    # Guardar si se especifica ruta
    if output_path:
        cv2.imwrite(output_path, processed)

    return processed
