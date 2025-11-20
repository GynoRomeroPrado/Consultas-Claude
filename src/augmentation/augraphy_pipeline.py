"""
Pipeline de Augmentación con Augraphy
Genera variantes sintéticas de facturas simulando:
- Impresoras matriciales de 9 pines
- Papel autocopiativo desvanecido
- Cintas de tinta gastadas
- Degradación por tiempo/uso
"""

import numpy as np
from typing import Optional, List, Tuple
import cv2
from pathlib import Path


try:
    from augraphy import *
except ImportError:
    print("Warning: Augraphy no está instalado. Instala con: pip install augraphy")


class InvoiceAugmentationPipeline:
    """
    Pipeline de augmentación especializado para facturas peruanas.
    Simula degradaciones realistas de documentos fiscales.
    """

    def __init__(
        self,
        intensity: str = "medium",
        simulate_dot_matrix: bool = True,
        simulate_faded_paper: bool = True,
        simulate_worn_ribbon: bool = True
    ):
        """
        Args:
            intensity: Intensidad de augmentación ("light", "medium", "heavy")
            simulate_dot_matrix: Simular impresión matricial
            simulate_faded_paper: Simular papel desvanecido
            simulate_worn_ribbon: Simular cinta de tinta gastada
        """
        self.intensity = intensity
        self.simulate_dot_matrix = simulate_dot_matrix
        self.simulate_faded_paper = simulate_faded_paper
        self.simulate_worn_ribbon = simulate_worn_ribbon

        # Configurar parámetros según intensidad
        self.intensity_params = self._get_intensity_params()

        # Construir pipeline
        self.pipeline = self._build_pipeline()

    def _get_intensity_params(self) -> dict:
        """Obtiene parámetros según el nivel de intensidad."""
        params = {
            "light": {
                "dot_matrix_opacity": (0.3, 0.5),
                "ink_bleed": (0.3, 0.5),
                "brightness": (0.9, 1.1),
                "noise": (0.01, 0.03)
            },
            "medium": {
                "dot_matrix_opacity": (0.5, 0.7),
                "ink_bleed": (0.5, 0.7),
                "brightness": (0.8, 1.2),
                "noise": (0.03, 0.05)
            },
            "heavy": {
                "dot_matrix_opacity": (0.7, 0.9),
                "ink_bleed": (0.7, 0.9),
                "brightness": (0.6, 1.4),
                "noise": (0.05, 0.08)
            }
        }
        return params.get(self.intensity, params["medium"])

    def _build_pipeline(self):
        """Construye el pipeline de augmentación con Augraphy."""
        try:
            # Lista de transformaciones
            augmentations = []

            # Fase 1: Ink - Simula degradación de tinta
            ink_phase = []

            if self.simulate_dot_matrix:
                # Simula patrón de matriz de puntos de impresora de 9 pines
                ink_phase.append(
                    DotMatrix(
                        dot_width_range=(1, 3),
                        dot_height_range=(1, 3),
                        dot_opacity_range=self.intensity_params["dot_matrix_opacity"],
                        p=0.8
                    )
                )

            if self.simulate_worn_ribbon:
                # Simula cinta de impresora gastada
                ink_phase.append(
                    InkBleed(
                        intensity_range=self.intensity_params["ink_bleed"],
                        kernel_size=(5, 5),
                        severity=(0.4, 0.7),
                        p=0.7
                    )
                )

            # Manchas de tinta aleatorias
            ink_phase.append(
                Markup(
                    num_lines_range=(1, 3),
                    markup_length_range=(10, 50),
                    markup_thickness_range=(1, 2),
                    markup_type="random",
                    p=0.3
                )
            )

            # Fase 2: Paper - Simula degradación del papel
            paper_phase = []

            if self.simulate_faded_paper:
                # Papel desvanecido/amarillento
                paper_phase.append(
                    ColorPaper(
                        hue_range=(20, 40),  # Tono amarillento
                        saturation_range=(10, 30),
                        p=0.6
                    )
                )

            # Textura del papel
            paper_phase.append(
                PaperFactory(
                    texture_path=None,  # Usa texturas por defecto
                    p=0.5
                )
            )

            # Arrugas y dobleces
            paper_phase.append(
                Folding(
                    fold_count=(1, 3),
                    fold_noise=0.1,
                    p=0.3
                )
            )

            # Fase 3: Post - Efectos post-procesamiento
            post_phase = []

            # Variación de brillo (común en escaneos)
            post_phase.append(
                Brightness(
                    brightness_range=self.intensity_params["brightness"],
                    p=1.0
                )
            )

            # Ruido de escaneo
            post_phase.append(
                Noise(
                    noise_type="gauss",
                    noise_iteration=(1, 2),
                    noise_value=self.intensity_params["noise"],
                    p=0.7
                )
            )

            # Compresión JPEG (artefactos de digitalización)
            post_phase.append(
                Jpeg(
                    quality_range=(60, 90),
                    p=0.5
                )
            )

            # Ligera rotación (documentos mal escaneados)
            post_phase.append(
                Geometric(
                    scale=(1.0, 1.0),
                    translation=(0, 0),
                    fliplr=0,
                    flipud=0,
                    crop=(),
                    rotate_range=(-3, 3),
                    p=0.5
                )
            )

            # Sombras de borde
            post_phase.append(
                BadPhotoCopy(
                    noise_mask=None,
                    noise_type=-1,
                    noise_side="random",
                    noise_iteration=(1, 2),
                    noise_size=(1, 3),
                    noise_value=(128, 196),
                    noise_sparsity=(0.3, 0.6),
                    noise_concentration=(0.1, 0.6),
                    blur_noise=True,
                    blur_noise_kernel=(3, 3),
                    wave_pattern=False,
                    edge_effect=True,
                    p=0.4
                )
            )

            # Construir pipeline completo
            pipeline = AugraphyPipeline(
                ink_phase=ink_phase,
                paper_phase=paper_phase,
                post_phase=post_phase
            )

            return pipeline

        except NameError:
            print("Augraphy no está disponible. Retornando None.")
            return None

    def augment_image(self, image: np.ndarray) -> np.ndarray:
        """
        Aplica augmentación a una imagen.

        Args:
            image: Imagen de entrada (numpy array)

        Returns:
            Imagen augmentada
        """
        if self.pipeline is None:
            print("Pipeline no disponible, retornando imagen original")
            return image

        # Asegurar que la imagen esté en el formato correcto
        if len(image.shape) == 2:
            # Escala de grises -> RGB
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            # RGBA -> RGB
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)

        # Aplicar pipeline
        augmented = self.pipeline.augment(image)

        return augmented["output"]

    def generate_variants(
        self,
        image: np.ndarray,
        num_variants: int = 5
    ) -> List[np.ndarray]:
        """
        Genera múltiples variantes augmentadas de una imagen.

        Args:
            image: Imagen original
            num_variants: Número de variantes a generar

        Returns:
            Lista de imágenes augmentadas
        """
        variants = []
        for _ in range(num_variants):
            augmented = self.augment_image(image)
            variants.append(augmented)
        return variants

    def augment_dataset(
        self,
        input_dir: str,
        output_dir: str,
        variants_per_image: int = 3,
        file_pattern: str = "*.png"
    ) -> dict:
        """
        Augmenta todo un dataset de imágenes.

        Args:
            input_dir: Directorio con imágenes originales
            output_dir: Directorio para guardar imágenes augmentadas
            variants_per_image: Número de variantes por imagen original
            file_pattern: Patrón de archivos a procesar

        Returns:
            Estadísticas del proceso
        """
        from tqdm import tqdm

        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        image_files = list(input_path.glob(file_pattern))

        stats = {
            "original_images": len(image_files),
            "variants_per_image": variants_per_image,
            "total_generated": 0,
            "failed": 0
        }

        for img_file in tqdm(image_files, desc="Augmenting dataset"):
            try:
                # Leer imagen
                image = cv2.imread(str(img_file))
                if image is None:
                    raise ValueError(f"Could not read {img_file}")

                # Guardar original también
                original_output = output_path / f"{img_file.stem}_original{img_file.suffix}"
                cv2.imwrite(str(original_output), image)

                # Generar variantes
                variants = self.generate_variants(image, variants_per_image)

                # Guardar variantes
                for i, variant in enumerate(variants, 1):
                    variant_output = output_path / f"{img_file.stem}_aug_{i}{img_file.suffix}"
                    cv2.imwrite(str(variant_output), variant)
                    stats["total_generated"] += 1

            except Exception as e:
                print(f"Error procesando {img_file}: {e}")
                stats["failed"] += 1

        return stats


def create_light_pipeline() -> InvoiceAugmentationPipeline:
    """Crea pipeline de augmentación ligera."""
    return InvoiceAugmentationPipeline(intensity="light")


def create_medium_pipeline() -> InvoiceAugmentationPipeline:
    """Crea pipeline de augmentación media (recomendado)."""
    return InvoiceAugmentationPipeline(intensity="medium")


def create_heavy_pipeline() -> InvoiceAugmentationPipeline:
    """Crea pipeline de augmentación intensa."""
    return InvoiceAugmentationPipeline(intensity="heavy")


def augment_invoice_image(
    image_path: str,
    output_path: str,
    num_variants: int = 3,
    intensity: str = "medium"
) -> List[str]:
    """
    Función de conveniencia para augmentar una factura.

    Args:
        image_path: Ruta a la imagen original
        output_path: Directorio para guardar variantes
        num_variants: Número de variantes a generar
        intensity: Intensidad ("light", "medium", "heavy")

    Returns:
        Lista de rutas de imágenes generadas
    """
    # Leer imagen
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")

    # Crear pipeline
    pipeline = InvoiceAugmentationPipeline(intensity=intensity)

    # Generar variantes
    variants = pipeline.generate_variants(image, num_variants)

    # Guardar
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_name = Path(image_path).stem
    saved_paths = []

    for i, variant in enumerate(variants, 1):
        output_file = output_dir / f"{input_name}_variant_{i}.png"
        cv2.imwrite(str(output_file), variant)
        saved_paths.append(str(output_file))

    return saved_paths
