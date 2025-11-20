"""
Módulo de Optimización y Exportación ONNX
Exporta el modelo Donut a formato ONNX con cuantización INT8
para despliegue eficiente en CPU.
"""

import torch
import onnx
import onnxruntime as ort
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from tqdm import tqdm


class ONNXExporter:
    """
    Exportador de modelos Donut a formato ONNX optimizado.
    """

    def __init__(
        self,
        model,
        processor,
        output_dir: str = "./onnx_models"
    ):
        """
        Args:
            model: Modelo Donut entrenado
            processor: Procesador Donut
            output_dir: Directorio de salida para modelos ONNX
        """
        self.model = model
        self.processor = processor
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    def export_encoder(
        self,
        output_path: Optional[str] = None,
        opset_version: int = 14
    ) -> str:
        """
        Exporta el encoder (Swin Transformer) a ONNX.

        Args:
            output_path: Ruta de salida (None usa default)
            opset_version: Versión de opset ONNX

        Returns:
            Ruta del modelo exportado
        """
        if output_path is None:
            output_path = self.output_dir / "encoder.onnx"
        else:
            output_path = Path(output_path)

        print("Exporting encoder to ONNX...")

        # Crear input dummy
        image_size = self.model.encoder.config.image_size
        dummy_input = torch.randn(
            1, 3, image_size[0], image_size[1],
            device=self.device
        )

        # Exportar
        torch.onnx.export(
            self.model.encoder,
            dummy_input,
            str(output_path),
            input_names=["pixel_values"],
            output_names=["encoder_hidden_states"],
            dynamic_axes={
                "pixel_values": {0: "batch_size"},
                "encoder_hidden_states": {0: "batch_size"}
            },
            opset_version=opset_version,
            do_constant_folding=True
        )

        print(f"Encoder exported to {output_path}")
        return str(output_path)

    def export_decoder(
        self,
        output_path: Optional[str] = None,
        opset_version: int = 14
    ) -> str:
        """
        Exporta el decoder (BART) a ONNX.

        Args:
            output_path: Ruta de salida
            opset_version: Versión de opset ONNX

        Returns:
            Ruta del modelo exportado
        """
        if output_path is None:
            output_path = self.output_dir / "decoder.onnx"
        else:
            output_path = Path(output_path)

        print("Exporting decoder to ONNX...")

        # Crear inputs dummy
        batch_size = 1
        seq_len = 10
        hidden_size = self.model.decoder.config.hidden_size

        dummy_decoder_input_ids = torch.randint(
            0, self.model.decoder.config.vocab_size,
            (batch_size, seq_len),
            device=self.device
        )

        dummy_encoder_hidden_states = torch.randn(
            batch_size, 100, hidden_size,
            device=self.device
        )

        # Exportar
        torch.onnx.export(
            self.model.decoder,
            (dummy_decoder_input_ids, dummy_encoder_hidden_states),
            str(output_path),
            input_names=["input_ids", "encoder_hidden_states"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "encoder_hidden_states": {0: "batch_size", 1: "encoder_sequence_length"},
                "logits": {0: "batch_size", 1: "sequence_length"}
            },
            opset_version=opset_version,
            do_constant_folding=True
        )

        print(f"Decoder exported to {output_path}")
        return str(output_path)

    def export_full_model(
        self,
        encoder_path: Optional[str] = None,
        decoder_path: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Exporta encoder y decoder por separado.

        Args:
            encoder_path: Ruta para encoder
            decoder_path: Ruta para decoder

        Returns:
            Diccionario con rutas de los modelos exportados
        """
        paths = {
            "encoder": self.export_encoder(encoder_path),
            "decoder": self.export_decoder(decoder_path)
        }

        # Guardar configuración
        config_path = self.output_dir / "config.json"
        import json
        with open(config_path, 'w') as f:
            json.dump({
                "encoder_path": paths["encoder"],
                "decoder_path": paths["decoder"],
                "image_size": list(self.model.encoder.config.image_size),
            }, f, indent=2)

        print(f"Configuration saved to {config_path}")

        return paths

    def quantize_model(
        self,
        onnx_model_path: str,
        quantized_model_path: Optional[str] = None,
        quantization_mode: str = "int8"
    ) -> str:
        """
        Aplica cuantización al modelo ONNX.

        Args:
            onnx_model_path: Ruta al modelo ONNX original
            quantized_model_path: Ruta de salida (None usa default)
            quantization_mode: Tipo de cuantización ("int8" o "uint8")

        Returns:
            Ruta del modelo cuantizado
        """
        from onnxruntime.quantization import quantize_dynamic, QuantType

        if quantized_model_path is None:
            base_path = Path(onnx_model_path)
            quantized_model_path = base_path.parent / f"{base_path.stem}_quantized.onnx"

        print(f"Quantizing model: {onnx_model_path}")

        # Seleccionar tipo de cuantización
        quant_type = QuantType.QInt8 if quantization_mode == "int8" else QuantType.QUInt8

        # Cuantización dinámica (más fácil, no requiere dataset)
        quantize_dynamic(
            model_input=onnx_model_path,
            model_output=str(quantized_model_path),
            weight_type=quant_type,
            optimize_model=True
        )

        # Verificar tamaño
        original_size = Path(onnx_model_path).stat().st_size / (1024 * 1024)
        quantized_size = Path(quantized_model_path).stat().st_size / (1024 * 1024)
        reduction = ((original_size - quantized_size) / original_size) * 100

        print(f"Original size: {original_size:.2f} MB")
        print(f"Quantized size: {quantized_size:.2f} MB")
        print(f"Size reduction: {reduction:.1f}%")

        return str(quantized_model_path)

    def export_and_quantize(
        self,
        quantize_encoder: bool = True,
        quantize_decoder: bool = True
    ) -> Dict[str, str]:
        """
        Pipeline completo: exporta y cuantiza el modelo.

        Args:
            quantize_encoder: Si cuantizar el encoder
            quantize_decoder: Si cuantizar el decoder

        Returns:
            Diccionario con todas las rutas de modelos
        """
        print("\n" + "="*60)
        print("ONNX Export and Quantization Pipeline")
        print("="*60 + "\n")

        # Exportar modelos
        paths = self.export_full_model()

        # Cuantizar encoder
        if quantize_encoder:
            encoder_quantized = self.quantize_model(
                paths["encoder"],
                quantization_mode="int8"
            )
            paths["encoder_quantized"] = encoder_quantized

        # Cuantizar decoder
        if quantize_decoder:
            decoder_quantized = self.quantize_model(
                paths["decoder"],
                quantization_mode="int8"
            )
            paths["decoder_quantized"] = decoder_quantized

        print("\n" + "="*60)
        print("Export and quantization completed!")
        print("="*60 + "\n")

        return paths


class ONNXInferenceEngine:
    """
    Motor de inferencia usando modelos ONNX optimizados.
    """

    def __init__(
        self,
        encoder_path: str,
        decoder_path: str,
        processor,
        use_gpu: bool = False
    ):
        """
        Args:
            encoder_path: Ruta al encoder ONNX
            decoder_path: Ruta al decoder ONNX
            processor: Procesador Donut
            use_gpu: Si usar GPU (requiere onnxruntime-gpu)
        """
        self.processor = processor

        # Configurar providers
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if use_gpu else ['CPUExecutionProvider']

        # Cargar modelos
        print("Loading ONNX models...")
        self.encoder_session = ort.InferenceSession(encoder_path, providers=providers)
        self.decoder_session = ort.InferenceSession(decoder_path, providers=providers)

        print(f"Encoder provider: {self.encoder_session.get_providers()}")
        print(f"Decoder provider: {self.decoder_session.get_providers()}")

    def run_encoder(self, pixel_values: np.ndarray) -> np.ndarray:
        """
        Ejecuta el encoder ONNX.

        Args:
            pixel_values: Imagen preprocesada

        Returns:
            Hidden states del encoder
        """
        encoder_outputs = self.encoder_session.run(
            None,
            {"pixel_values": pixel_values}
        )
        return encoder_outputs[0]

    def run_decoder(
        self,
        input_ids: np.ndarray,
        encoder_hidden_states: np.ndarray
    ) -> np.ndarray:
        """
        Ejecuta el decoder ONNX.

        Args:
            input_ids: IDs de tokens de entrada
            encoder_hidden_states: Estados del encoder

        Returns:
            Logits del decoder
        """
        decoder_outputs = self.decoder_session.run(
            None,
            {
                "input_ids": input_ids,
                "encoder_hidden_states": encoder_hidden_states
            }
        )
        return decoder_outputs[0]

    def predict(
        self,
        image: np.ndarray,
        max_length: int = 768
    ) -> Dict[str, Any]:
        """
        Realiza predicción completa en una imagen.

        Args:
            image: Imagen de entrada
            max_length: Longitud máxima de generación

        Returns:
            Diccionario con resultados parseados
        """
        # Preprocesar imagen
        pixel_values = self.processor(
            image,
            return_tensors="np"
        ).pixel_values

        # Encoder
        encoder_hidden_states = self.run_encoder(pixel_values)

        # Decoder autoregresivo (simplificado)
        # En producción, implementar beam search completo
        input_ids = np.array([[self.processor.tokenizer.bos_token_id]], dtype=np.int64)

        generated_tokens = []
        for _ in range(max_length):
            logits = self.run_decoder(input_ids, encoder_hidden_states)
            next_token = np.argmax(logits[0, -1, :])

            if next_token == self.processor.tokenizer.eos_token_id:
                break

            generated_tokens.append(next_token)
            input_ids = np.append(input_ids, [[next_token]], axis=1)

        # Decodificar
        text = self.processor.tokenizer.decode(generated_tokens, skip_special_tokens=True)

        # Parsear JSON
        import json
        try:
            result = json.loads(text)
        except:
            result = {"raw_text": text}

        return result

    def benchmark(
        self,
        test_image: np.ndarray,
        num_iterations: int = 10
    ) -> Dict[str, float]:
        """
        Mide el rendimiento del modelo.

        Args:
            test_image: Imagen de prueba
            num_iterations: Número de iteraciones

        Returns:
            Estadísticas de rendimiento
        """
        import time

        times = []

        for _ in tqdm(range(num_iterations), desc="Benchmarking"):
            start = time.time()
            _ = self.predict(test_image)
            end = time.time()
            times.append(end - start)

        return {
            "mean_time": np.mean(times),
            "std_time": np.std(times),
            "min_time": np.min(times),
            "max_time": np.max(times),
            "throughput": 1.0 / np.mean(times)  # images/second
        }


def export_model_to_onnx(
    model_path: str,
    output_dir: str,
    quantize: bool = True
) -> Dict[str, str]:
    """
    Función de conveniencia para exportar un modelo a ONNX.

    Args:
        model_path: Ruta al modelo entrenado
        output_dir: Directorio de salida
        quantize: Si aplicar cuantización

    Returns:
        Diccionario con rutas de modelos exportados
    """
    from transformers import VisionEncoderDecoderModel, DonutProcessor

    # Cargar modelo
    model = VisionEncoderDecoderModel.from_pretrained(model_path)
    processor = DonutProcessor.from_pretrained(model_path)

    # Exportar
    exporter = ONNXExporter(model, processor, output_dir)

    if quantize:
        return exporter.export_and_quantize()
    else:
        return exporter.export_full_model()
