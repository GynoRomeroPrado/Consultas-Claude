# Guía de Inicio Rápido

Esta guía te llevará desde la instalación hasta tener un modelo entrenado y optimizado en 7 semanas.

## 📋 Prerrequisitos

- Python 3.8+
- 16 GB RAM (32 GB recomendado)
- GPU con 8+ GB VRAM (opcional pero muy recomendado para entrenamiento)
- 50 GB de espacio en disco

## ⚡ Instalación Rápida

```bash
# 1. Clonar repositorio
git clone <url-del-repo>
cd Consultas-Claude

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Instalar soporte GPU
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## 🗓️ Plan de 7 Semanas

### **Semanas 1-2: Preparación de Datos**

#### Paso 1: Organizar tus facturas originales

```bash
# Copiar tus facturas a data/raw/
cp /ruta/a/tus/facturas/*.png data/raw/
```

#### Paso 2: Preprocesar imágenes

```bash
python scripts/preprocess_images.py \
  --input-dir data/raw \
  --output-dir data/processed \
  --target-width 1920 \
  --target-height 2560 \
  --save-metadata
```

#### Paso 3: Augmentar dataset (objetivo: 15,000-25,000 imágenes)

```bash
# Generar 3 variantes por imagen
python scripts/augment_dataset.py \
  --input-dir data/processed \
  --output-dir data/augmented \
  --variants 3 \
  --intensity medium
```

**Resultado esperado**: Si tienes 5,000 facturas originales, ahora tendrás ~20,000 imágenes.

---

### **Semana 3: Preparación del Entrenamiento**

#### Paso 4: Preparar dataset para entrenamiento

Necesitas crear un dataset personalizado. Ejemplo básico:

```python
# crear_dataset.py
from torch.utils.data import Dataset
from PIL import Image
import json

class InvoiceDataset(Dataset):
    def __init__(self, image_dir, annotations_file, processor):
        self.image_dir = image_dir
        self.processor = processor

        # Cargar anotaciones (debes tener un JSON con los datos extraídos)
        with open(annotations_file) as f:
            self.annotations = json.load(f)

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, idx):
        # Cargar imagen
        img_path = self.annotations[idx]['image_path']
        image = Image.open(img_path).convert("RGB")

        # Obtener ground truth
        ground_truth = self.annotations[idx]['data']

        # Procesar con Donut processor
        pixel_values = self.processor(image, return_tensors="pt").pixel_values

        # Crear target text en formato JSON
        target_text = json.dumps(ground_truth, ensure_ascii=False)
        labels = self.processor.tokenizer(
            target_text,
            add_special_tokens=True,
            max_length=768,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        ).input_ids

        return {
            "pixel_values": pixel_values.squeeze(),
            "labels": labels.squeeze()
        }
```

---

### **Semanas 4-6: Entrenamiento Multi-Fase**

#### Paso 5: Ejecutar entrenamiento

```bash
python scripts/train_model.py \
  --synthetic-data-dir data/augmented \
  --real-data-dir data/processed \
  --output-dir checkpoints \
  --num-epochs 30 \
  --batch-size 2 \
  --phase1-epochs 15 \
  --phase2-epochs 10 \
  --phase3-epochs 5
```

**Nota**: El entrenamiento tomará varios días dependiendo de tu hardware.

**Monitoreo con TensorBoard**:

```bash
tensorboard --logdir logs
# Abrir http://localhost:6006
```

---

### **Semana 7: Optimización y Despliegue**

#### Paso 6: Exportar a ONNX con cuantización

```bash
python scripts/export_to_onnx.py \
  --model-path checkpoints/final_model \
  --output-dir onnx_models \
  --benchmark \
  --test-image data/processed/ejemplo.png
```

#### Paso 7: Probar el modelo optimizado

```python
# test_onnx_model.py
from src.optimization.onnx_exporter import ONNXInferenceEngine
from transformers import DonutProcessor
import cv2

# Cargar modelo ONNX
processor = DonutProcessor.from_pretrained("checkpoints/final_model")
engine = ONNXInferenceEngine(
    encoder_path="onnx_models/encoder_quantized.onnx",
    decoder_path="onnx_models/decoder_quantized.onnx",
    processor=processor,
    use_gpu=False
)

# Inferencia
image = cv2.imread("data/processed/test_invoice.png")
result = engine.predict(image)
print(result)
```

---

## 🧪 Validación de Resultados

### Validar RUC extraído

```python
from src.validation.sunat_validator import validate_ruc

ruc = result.get("ruc_e", "")
is_valid, error = validate_ruc(ruc)

if not is_valid:
    print(f"RUC inválido: {error}")
```

### Validar totales de factura

```python
from src.validation.sunat_validator import validate_invoice

validation_result = validate_invoice(result)

if not validation_result["valid"]:
    print("Errores encontrados:")
    for error in validation_result["errors"]:
        print(f"  - {error}")
```

---

## 📊 Métricas de Éxito

Al finalizar, deberías tener:

- ✅ **Precisión**: >95% en campos principales (RUC, totales, fecha)
- ✅ **Latencia**: <500ms por factura en CPU
- ✅ **Validación**: >99% de RUCs matemáticamente válidos
- ✅ **Tamaño**: Modelo ~500 MB (cuantizado)

---

## 🔧 Troubleshooting

### Error: CUDA out of memory

Solución: Reducir `batch_size` a 1 o deshabilitar `fp16`:

```bash
python scripts/train_model.py --batch-size 1 ...
```

### Error: Augraphy no funciona

Verificar instalación:

```bash
pip install augraphy --upgrade
```

### Modelo no converge

- Verificar que las anotaciones sean correctas
- Aumentar `warmup_steps` a 1000
- Reducir `learning_rate` a 1e-5

---

## 📚 Siguiente Paso

Una vez completado el entrenamiento básico, consulta la documentación avanzada:

- `README.md` - Documentación completa
- `configs/` - Ajustar hiperparámetros
- `src/` - Personalizar componentes

---

**¿Preguntas?** Abre un issue en GitHub.
