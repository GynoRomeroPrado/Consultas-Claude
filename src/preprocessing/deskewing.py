"""
Módulo de Corrección de Inclinación (Deskewing)
Implementa algoritmo de deskewing basado en proyección de perfil
para corregir la rotación de documentos escaneados.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
from scipy.ndimage import rotate as scipy_rotate


class DeskewProcessor:
    """
    Procesador de corrección de inclinación para documentos escaneados.
    Utiliza proyección de perfil y análisis de varianza para detectar el ángulo óptimo.
    """

    def __init__(
        self,
        angle_range: Tuple[float, float] = (-10.0, 10.0),
        angle_step: float = 0.1,
        background_color: int = 255
    ):
        """
        Args:
            angle_range: Rango de ángulos a evaluar (min, max) en grados
            angle_step: Paso de incremento para búsqueda de ángulo
            background_color: Color de fondo para rotación (255=blanco, 0=negro)
        """
        self.angle_range = angle_range
        self.angle_step = angle_step
        self.background_color = background_color

    def compute_projection_profile(self, image: np.ndarray) -> np.ndarray:
        """
        Calcula el perfil de proyección horizontal de la imagen.

        Args:
            image: Imagen binaria

        Returns:
            Array con la suma de píxeles por fila
        """
        return np.sum(image, axis=1)

    def calculate_variance(self, projection: np.ndarray) -> float:
        """
        Calcula la varianza del perfil de proyección.
        Mayor varianza indica mejor alineación del texto.

        Args:
            projection: Perfil de proyección

        Returns:
            Varianza del perfil
        """
        return np.var(projection)

    def detect_skew_angle(self, image: np.ndarray) -> float:
        """
        Detecta el ángulo de inclinación óptimo usando proyección de perfil.

        El algoritmo funciona porque cuando el texto está perfectamente
        horizontal, la proyección vertical tiene mayor varianza
        (picos altos en líneas de texto, valles bajos en espacios).

        Args:
            image: Imagen en escala de grises o binaria

        Returns:
            Ángulo de inclinación en grados
        """
        # Convertir a escala de grises si es necesario
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Binarizar
        _, binary = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        best_angle = 0.0
        max_variance = 0.0

        # Búsqueda del ángulo óptimo
        angles = np.arange(
            self.angle_range[0],
            self.angle_range[1],
            self.angle_step
        )

        for angle in angles:
            # Rotar imagen
            rotated = self._rotate_image(binary, angle)

            # Calcular proyección y varianza
            projection = self.compute_projection_profile(rotated)
            variance = self.calculate_variance(projection)

            # Actualizar si encontramos mejor varianza
            if variance > max_variance:
                max_variance = variance
                best_angle = angle

        return best_angle

    def detect_skew_angle_fast(self, image: np.ndarray) -> float:
        """
        Versión rápida de detección usando transformada de Hough.

        Args:
            image: Imagen en escala de grises

        Returns:
            Ángulo de inclinación en grados
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Detectar bordes
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Transformada de Hough para detectar líneas
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None:
            return 0.0

        # Calcular ángulos de las líneas detectadas
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            # Filtrar ángulos razonables
            if -45 < angle < 45:
                angles.append(angle)

        if not angles:
            return 0.0

        # Usar la mediana de los ángulos
        return np.median(angles)

    def _rotate_image(
        self,
        image: np.ndarray,
        angle: float,
        background: Optional[int] = None
    ) -> np.ndarray:
        """
        Rota la imagen en el ángulo especificado.

        Args:
            image: Imagen a rotar
            angle: Ángulo de rotación en grados
            background: Color de fondo (None usa self.background_color)

        Returns:
            Imagen rotada
        """
        if background is None:
            background = self.background_color

        height, width = image.shape[:2]
        center = (width // 2, height // 2)

        # Obtener matriz de rotación
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Calcular nuevo tamaño de imagen
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))

        # Ajustar matriz de rotación para el nuevo tamaño
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]

        # Aplicar rotación
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (new_width, new_height),
            borderValue=background
        )

        return rotated

    def deskew(
        self,
        image: np.ndarray,
        method: str = "projection"
    ) -> Tuple[np.ndarray, float]:
        """
        Corrige la inclinación de la imagen.

        Args:
            image: Imagen de entrada
            method: Método de detección ("projection" o "hough")

        Returns:
            Tupla (imagen corregida, ángulo detectado)
        """
        # Detectar ángulo
        if method == "projection":
            angle = self.detect_skew_angle(image)
        elif method == "hough":
            angle = self.detect_skew_angle_fast(image)
        else:
            raise ValueError(f"Método desconocido: {method}")

        # Corregir rotación
        corrected = self._rotate_image(image, -angle)

        return corrected, angle

    def deskew_with_border_removal(self, image: np.ndarray) -> np.ndarray:
        """
        Corrige inclinación y elimina bordes negros resultantes.

        Args:
            image: Imagen de entrada

        Returns:
            Imagen corregida sin bordes
        """
        # Corregir inclinación
        deskewed, _ = self.deskew(image)

        # Encontrar región de contenido (eliminar bordes negros)
        if len(deskewed.shape) == 3:
            gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY)
        else:
            gray = deskewed

        # Encontrar contornos
        _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
        coords = cv2.findNonZero(thresh)

        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            cropped = deskewed[y:y+h, x:x+w]
            return cropped

        return deskewed


def deskew_invoice_image(
    image_path: str,
    output_path: Optional[str] = None,
    method: str = "projection"
) -> Tuple[np.ndarray, float]:
    """
    Función de conveniencia para corregir inclinación de una factura.

    Args:
        image_path: Ruta a la imagen de entrada
        output_path: Ruta opcional para guardar el resultado
        method: Método de detección ("projection" o "hough")

    Returns:
        Tupla (imagen corregida, ángulo detectado)
    """
    # Leer imagen
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")

    # Procesar
    processor = DeskewProcessor()
    deskewed, angle = processor.deskew(image, method=method)

    # Guardar si se especifica ruta
    if output_path:
        cv2.imwrite(output_path, deskewed)

    return deskewed, angle
