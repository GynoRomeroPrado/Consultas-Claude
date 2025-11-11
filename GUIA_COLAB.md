# 🚀 Guía Completa: Entrenar LayoutLMv3 en Google Colab

Esta guía te lleva paso a paso desde cero hasta tener un modelo LayoutLMv3 entrenado para extraer campos de tus facturas usando Google Colab.

---

## 📋 ¿Qué necesitas?

### Requisitos Previos

1. **Cuenta de Google** (para usar Colab)
2. **Facturas en PDF** (mínimo 10, recomendado 50+)
3. **Anotaciones en JSON** (un JSON por cada PDF con campos anotados)

### Formato de Anotaciones JSON

Cada PDF debe tener un JSON con este formato:

```json
{
  "emisor_ruc": "20137291313",
  "emisor_nombre": "EMPRESA SAC",
  "fecha_emision": "2024-01-15",
  "total": "1500.00",
  "subtotal": "1271.19",
  "igv": "228.81",
  "receptor_nombre": "CLIENTE XYZ"
}
```

**Campos soportados**: Cualquier campo que quieras extraer (RUC, nombre, fechas, montos, etc.)

---

## 🎯 Paso a Paso

### Paso 1: Preparar Archivos Localmente

Antes de subir a Colab, organiza tus archivos localmente:

```
Mi_Proyecto_Facturas/
├── pdfs/
│   ├── factura_001.pdf
│   ├── factura_002.pdf
│   └── ...
└── anotaciones/
    ├── factura_001.json
    ├── factura_002.json
    └── ...
```

**⚠️ Importante**: Cada PDF debe tener un JSON con el mismo nombre.

---

### Paso 2: Abrir Google Colab

1. Ve a https://colab.research.google.com/
2. Haz clic en "File" → "Upload notebook"
3. Sube el archivo `COLAB_ENTRENAMIENTO_LAYOUTLMV3.ipynb`

O alternativamente:

1. Sube el notebook a tu Google Drive
2. Haz clic derecho → "Open with" → "Google Colaboratory"

---

### Paso 3: Configurar GPU

**⚠️ CRÍTICO**: Sin GPU, el entrenamiento será extremadamente lento.

1. En Colab, ve a **Runtime** → **Change runtime type**
2. En "Hardware accelerator", selecciona **GPU**
3. Tipo de GPU recomendado: **T4** (gratis en Colab)
4. Haz clic en **Save**

**Verificar GPU**:
```python
import torch
print(torch.cuda.is_available())  # Debe mostrar: True
print(torch.cuda.get_device_name(0))  # Debe mostrar: Tesla T4 o similar
```

---

### Paso 4: Instalar Dependencias

Ejecuta las celdas de instalación en orden:

#### 4.1 Dependencias Básicas (1-2 minutos)

```python
!pip install -q PyMuPDF>=1.23.0 pdfplumber>=0.10.0
!pip install -q rapidfuzz>=3.5.0
!pip install -q numpy pandas Pillow opencv-python
!pip install -q jsonschema tqdm click colorlog
```

#### 4.2 PaddleOCR (2-3 minutos)

```python
!pip install -q paddlepaddle-gpu>=2.5.0
!pip install -q paddleocr>=2.7.0
```

**Nota**: `paddlepaddle-gpu` es para GPU. Si usas CPU (no recomendado), instala `paddlepaddle` en su lugar.

#### 4.3 Transformers y PyTorch (1-2 minutos)

```python
!pip install -q transformers>=4.35.0
!pip install -q torch torchvision
```

**Tiempo total de instalación**: ~5 minutos

---

### Paso 5: Subir Archivos a Colab

Tienes **3 opciones** para subir tus archivos:

#### Opción A: Subir Manualmente (Más Simple)

1. En Colab, ejecuta:
```python
!mkdir -p "Datos extraidos de Originales/pdfs"
!mkdir -p "Datos extraidos de Originales/anotaciones"
```

2. En el panel izquierdo de Colab, haz clic en el icono de carpeta 📁

3. Navega a `Datos extraidos de Originales/pdfs`

4. Haz clic en los tres puntos → "Upload"

5. Sube todos tus PDFs

6. Repite para `Datos extraidos de Originales/anotaciones` con los JSONs

**⚠️ Advertencia**: Los archivos se borrarán cuando la sesión de Colab termine. Usa Google Drive para persistencia.

#### Opción B: Usar Google Drive (Recomendado)

1. Sube tus archivos a Google Drive en esta estructura:
```
Google Drive/
└── MiProyecto/
    ├── pdfs/
    └── anotaciones/
```

2. En Colab, monta Google Drive:
```python
from google.colab import drive
drive.mount('/content/drive')
```

3. Copia archivos:
```python
!cp -r '/content/drive/MyDrive/MiProyecto/pdfs' 'Datos extraidos de Originales/'
!cp -r '/content/drive/MyDrive/MiProyecto/anotaciones' 'Datos extraidos de Originales/'
```

#### Opción C: Clonar desde GitHub

Si tu proyecto está en GitHub:

```python
!git clone https://github.com/tu-usuario/tu-repo.git
%cd tu-repo
```

---

### Paso 6: Subir Scripts del Proyecto

Necesitas subir los scripts Python del proyecto a Colab:

**Archivos necesarios**:
```
src/
├── extractors/hybrid_extractor.py
├── matchers/advanced_fuzzy_matcher.py
├── normalizers/layoutlm_normalizer.py
├── validation/dataset_validator.py
├── exporters/layoutlm_exporter.py
├── preprocessing/image_processor.py
├── training/layoutlmv3_integration.py
├── cache/ocr_cache.py
└── utils/parallel_processor.py

Scripts raíz:
├── generar_dataset_avanzado.py
├── validar_dataset_layoutlm.py
└── entrenar_layoutlmv3.py
```

**Métodos de subida**:

1. **Manual**: Sube cada archivo usando el explorador de archivos de Colab

2. **GitHub**: Clona el repo completo

3. **Google Drive**: Sube la carpeta completa y cópiala:
```python
!cp -r '/content/drive/MyDrive/Consultas-Claude/src' .
!cp '/content/drive/MyDrive/Consultas-Claude/*.py' .
```

---

### Paso 7: Verificar Archivos

```python
import os
from pathlib import Path

pdfs = list(Path("Datos extraidos de Originales/pdfs").glob("*.pdf"))
jsons = list(Path("Datos extraidos de Originales/anotaciones").glob("*.json"))

print(f"PDFs encontrados: {len(pdfs)}")
print(f"JSONs encontrados: {len(jsons)}")

if pdfs:
    print("\nEjemplos de PDFs:")
    for pdf in pdfs[:5]:
        print(f"  - {pdf.name}")
```

**Resultado esperado**:
```
PDFs encontrados: 50
JSONs encontrados: 50

Ejemplos de PDFs:
  - factura_001.pdf
  - factura_002.pdf
  - factura_003.pdf
```

---

### Paso 8: Generar Dataset

Ahora generamos el dataset con todas las mejoras implementadas.

```python
!python generar_dataset_avanzado.py \
    --pdfs-dir "Datos extraidos de Originales/pdfs" \
    --json-dir "Datos extraidos de Originales/anotaciones" \
    --output-dir dataset_avanzado \
    --usar-ocr \
    --usar-gpu \
    --confianza-minima 0.75
```

**Parámetros**:
- `--pdfs-dir`: Carpeta con PDFs
- `--json-dir`: Carpeta con JSONs
- `--output-dir`: Donde guardar dataset
- `--usar-ocr`: Habilitar OCR para PDFs rasterizados
- `--usar-gpu`: Usar GPU para OCR (más rápido)
- `--confianza-minima`: Filtrar matches con confianza < 75%

**Tiempo estimado** (50 facturas):
- PDFs nativos: ~5 minutos
- PDFs rasterizados (con OCR): ~15 minutos

**Output esperado**:
```
================================================================================
GENERACIÓN DE DATASET AVANZADO
================================================================================

Procesando: 100%|██████████| 50/50 [15:23<00:00, 18.5s/it]

✅ GENERACIÓN COMPLETADA

Estadísticas:
  PDFs procesados: 50
  Páginas totales: 50
  Campos extraídos: 750
  Confianza promedio: 0.92

Dataset guardado en:
  - Coordenadas: dataset_avanzado/coordenadas/
  - Imágenes: dataset_avanzado/imagenes_paginas/
```

---

### Paso 9: Validar Dataset

Antes de entrenar, validamos que no haya errores:

```python
!python validar_dataset_layoutlm.py \
    --dataset-dir dataset_avanzado/coordenadas \
    --verbose
```

**Output esperado**:
```
================================================================================
VALIDACIÓN DE DATASET LAYOUTLM
================================================================================

Validando: 100%|██████████| 50/50 [00:02<00:00, 25.3it/s]

RESUMEN DE VALIDACIÓN:
  Archivos validados: 50
  Errores encontrados: 0
  Advertencias: 3

✅ Dataset válido para entrenamiento

Advertencias (no críticas):
  - 3 campos con aspect ratio > 20 (campos muy anchos/altos)
```

**⚠️ Si hay errores críticos**:
- Revisa los archivos mencionados
- Verifica que los JSONs tengan el formato correcto
- Asegúrate de que los valores en JSON coincidan con el PDF

---

### Paso 10: Entrenar LayoutLMv3

¡Ahora viene la parte importante! Entrenar el modelo.

```python
!python entrenar_layoutlmv3.py \
    --dataset-dir dataset_avanzado/coordenadas \
    --images-dir dataset_avanzado/imagenes_paginas \
    --output-dir modelo_entrenado \
    --epochs 10 \
    --batch-size 4 \
    --lr 5e-5
```

**Parámetros Críticos**:

| Parámetro | Descripción | Valores Recomendados |
|-----------|-------------|---------------------|
| `--epochs` | Número de épocas | 10-15 (dataset pequeño), 5-10 (dataset grande) |
| `--batch-size` | Tamaño de batch | 4 (16GB VRAM), 2 (8GB VRAM) |
| `--lr` | Learning rate | 5e-5 (default), 3e-5 (más conservador) |

**Tiempo estimado**:
- 50 facturas, 10 épocas, GPU T4: **30-45 minutos**
- 100 facturas, 10 épocas, GPU T4: **60-90 minutos**

**Output durante entrenamiento**:
```
================================================================================
ENTRENAMIENTO DE LAYOUTLMV3
================================================================================
Dataset: dataset_avanzado/coordenadas
Modelo base: microsoft/layoutlmv3-base
Épocas: 10
Batch size: 4
Learning rate: 5e-5
GPU: Sí

📊 Preparando dataset...
   Número de labels: 15
   Campos: ['O', 'emisor_ruc', 'emisor_nombre', 'total', 'fecha']...

📁 Cargando dataset...
   Total samples: 50
   Train: 40 samples
   Val: 10 samples

🤖 Cargando modelo microsoft/layoutlmv3-base...
   Modelo cargado en: cuda

🚀 Iniciando entrenamiento...

Epoch 1/10: 100%|██████████| 10/10 [02:15<00:00, 13.5s/it] loss: 2.1234
Epoch 2/10: 100%|██████████| 10/10 [02:10<00:00, 13.0s/it] loss: 1.5678
...
Epoch 10/10: 100%|██████████| 10/10 [02:08<00:00, 12.8s/it] loss: 0.1234

================================================================================
✅ ENTRENAMIENTO COMPLETADO
================================================================================

📊 Evaluando modelo...
   Eval Loss: 0.1234

💾 Modelo guardado en: modelo_entrenado/modelo_final
```

**⚠️ Si ves "CUDA Out of Memory"**:
```python
# Reducir batch size
!python entrenar_layoutlmv3.py ... --batch-size 2

# O usar CPU (MUY lento)
!python entrenar_layoutlmv3.py ... --cpu
```

---

### Paso 11: Revisar Resultados

Después del entrenamiento, revisamos el modelo:

```python
import json
from pathlib import Path

# Cargar label map
label_map_path = "modelo_entrenado/modelo_final/label_map.json"
with open(label_map_path, 'r') as f:
    label_map = json.load(f)

print("="*60)
print("MODELO ENTRENADO - RESUMEN")
print("="*60)
print(f"\nNúmero de campos: {len(label_map['campo_to_id'])}")
print("\nCampos que el modelo puede detectar:")
for campo in sorted(label_map['campo_to_id'].keys()):
    if campo != 'O':  # Omitir "O" (no es campo)
        print(f"  ✓ {campo}")
```

**Output esperado**:
```
============================================================
MODELO ENTRENADO - RESUMEN
============================================================

Número de campos: 15

Campos que el modelo puede detectar:
  ✓ emisor_ruc
  ✓ emisor_nombre
  ✓ fecha_emision
  ✓ total
  ✓ subtotal
  ✓ igv
  ✓ receptor_nombre
  ...
```

---

### Paso 12: Descargar Modelo

Descarga el modelo entrenado a tu computadora:

```python
# Comprimir modelo
!zip -r modelo_layoutlmv3_facturas.zip modelo_entrenado/modelo_final

# Descargar
from google.colab import files
files.download('modelo_layoutlmv3_facturas.zip')
```

**Tamaño del archivo**: ~500 MB

**Alternativa**: Guardar en Google Drive:
```python
!cp modelo_layoutlmv3_facturas.zip '/content/drive/MyDrive/'
```

---

### Paso 13: Usar el Modelo (Opcional - en Colab)

Puedes probar el modelo directamente en Colab:

```python
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor
from PIL import Image
import torch
import json

# Cargar modelo
model_path = "modelo_entrenado/modelo_final"
model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
processor = LayoutLMv3Processor.from_pretrained(model_path)

# Cargar label map
with open(f"{model_path}/label_map.json", 'r') as f:
    label_map = json.load(f)
    id_to_campo = {int(k): v for k, v in label_map['id_to_campo'].items()}

print("✅ Modelo cargado!")

# Función de predicción
def predecir_factura(image_path, words, boxes):
    """
    Predice campos en una factura.

    Args:
        image_path: Ruta a imagen de factura
        words: Lista de palabras
        boxes: Lista de bboxes normalizados (0-1000)
    """
    image = Image.open(image_path).convert("RGB")

    # Procesar
    encoding = processor(
        image, words, boxes=boxes,
        truncation=True, max_length=512,
        return_tensors="pt"
    )

    # Predecir
    with torch.no_grad():
        outputs = model(**encoding)
        predictions = outputs.logits.argmax(-1).squeeze().tolist()

    # Decodificar
    resultados = []
    for word, box, pred_id in zip(words, boxes, predictions):
        campo = id_to_campo.get(pred_id, 'O')
        if campo != 'O':
            resultados.append({
                'campo': campo,
                'texto': word,
                'bbox': box
            })

    return resultados

# Ejemplo de uso
# predecir_factura("factura_test.jpg", ["20137291313", ...], [[10, 20, 100, 30], ...])
```

---

## 📊 Consejos para Mejorar Resultados

### 1. Más Datos = Mejor Modelo

| Facturas | Precisión Esperada |
|----------|-------------------|
| 10-20 | 60-70% |
| 30-50 | 75-85% |
| 50-100 | 85-92% |
| 100+ | 90-95% |

### 2. Calidad de Anotaciones

✅ **Buenas prácticas**:
- Anota exactamente como aparece en el PDF
- Incluye todos los campos visibles
- Verifica que valores coincidan

❌ **Evita**:
- Corregir valores (anota lo que dice, aunque esté mal)
- Omitir campos difíciles
- Abreviar o modificar texto

### 3. Ajuste de Hiperparámetros

Si el modelo no funciona bien:

**Underfitting** (loss muy alto):
```python
# Aumentar épocas
--epochs 20

# Aumentar learning rate
--lr 1e-4
```

**Overfitting** (train loss bajo, val loss alto):
```python
# Reducir épocas
--epochs 5

# Reducir learning rate
--lr 3e-5

# Agregar más datos
```

### 4. PDFs de Mala Calidad

Si tienes PDFs escaneados de mala calidad:

```python
# Usar OCR obligatorio
--usar-ocr

# Reducir confianza mínima
--confianza-minima 0.6

# Verificar preprocesamiento de imagen está habilitado
# (ya incluido en generar_dataset_avanzado.py)
```

---

## 🔧 Troubleshooting Común

### Error: "No module named 'transformers'"

**Solución**: Vuelve a ejecutar la celda de instalación:
```python
!pip install transformers torch
```

### Error: "CUDA out of memory"

**Solución 1**: Reducir batch size
```python
--batch-size 2  # o incluso 1
```

**Solución 2**: Limpiar memoria
```python
import torch
torch.cuda.empty_cache()
```

**Solución 3**: Reiniciar runtime
- Runtime → Restart runtime

### Error: "PaddleOCR not found"

**Solución**:
```python
!pip install paddlepaddle-gpu paddleocr
```

### Warning: "Low confidence matches"

**Causa**: Fuzzy matching no encuentra coincidencias exactas

**Solución**: Verificar que:
1. Valores en JSON coincidan con PDF
2. No haya errores de tipeo
3. Formatos sean consistentes (ej: fechas)

### Dataset muy lento

**Causa**: OCR tarda mucho

**Soluciones**:
1. Verificar GPU habilitado: `--usar-gpu`
2. Usar cache (segunda vez será 10x más rápido)
3. Reducir calidad de imagen si es muy alta

---

## 💡 Mejores Prácticas

### 1. Organización de Archivos

```
Google Drive/
└── Proyecto_Facturas/
    ├── datos/
    │   ├── pdfs/
    │   └── anotaciones/
    ├── datasets/
    │   └── dataset_v1/
    ├── modelos/
    │   ├── modelo_v1/
    │   └── modelo_v2/
    └── notebooks/
        └── entrenamiento.ipynb
```

### 2. Versionado de Modelos

Guarda cada versión con fecha y parámetros:

```
modelos/
├── modelo_2024-01-15_e10_bs4/
├── modelo_2024-01-20_e15_bs4/
└── modelo_2024-01-25_e20_bs2/
```

### 3. Logging

Guarda logs de cada entrenamiento:

```python
# Redirigir output a archivo
!python entrenar_layoutlmv3.py ... 2>&1 | tee training_log.txt

# Guardar en Drive
!cp training_log.txt '/content/drive/MyDrive/logs/'
```

### 4. Checkpoints

El script automáticamente guarda checkpoints. Para recuperar:

```python
# Si el entrenamiento se interrumpe, continúa desde último checkpoint
from transformers import Trainer

trainer = Trainer(...)
trainer.train(resume_from_checkpoint=True)
```

---

## 📈 Monitoreo del Entrenamiento

### Ver Progreso en Tiempo Real

El script muestra:
- ✅ Loss por época
- ✅ Tiempo por iteración
- ✅ ETA de finalización

### Métricas a Observar

| Métrica | Bueno | Malo | Acción |
|---------|-------|------|--------|
| Train Loss | < 0.5 después de 10 épocas | > 1.0 | Más épocas o LR más alto |
| Eval Loss | Similar a Train Loss | >> Train Loss | Más datos o regularización |
| Tiempo/iteración | < 15s | > 30s | Verificar GPU, reducir batch size |

---

## 🎯 Resumen del Flujo Completo

```
1. Preparar archivos (PDFs + JSONs)
   ↓
2. Abrir Colab + Configurar GPU
   ↓
3. Instalar dependencias (~5 min)
   ↓
4. Subir archivos a Colab
   ↓
5. Generar dataset (~15 min)
   ↓
6. Validar dataset (~2 min)
   ↓
7. Entrenar modelo (~45 min)
   ↓
8. Descargar modelo
   ↓
9. ¡Usar en producción!
```

**Tiempo total**: ~1-1.5 horas

---

## 🚀 Próximos Pasos

Después de entrenar el modelo:

1. **Probar con nuevas facturas** no vistas durante entrenamiento
2. **Medir precisión** en conjunto de test
3. **Iterar**:
   - Agregar más datos
   - Ajustar hiperparámetros
   - Re-entrenar

4. **Desplegar**:
   - Usar en aplicación local
   - Crear API REST
   - Integrar con sistema existente

---

## 📚 Recursos Adicionales

- **Documentación LayoutLMv3**: https://huggingface.co/microsoft/layoutlmv3-base
- **Google Colab FAQ**: https://research.google.com/colaboratory/faq.html
- **Transformers Docs**: https://huggingface.co/docs/transformers

---

## ✅ Checklist Final

Antes de empezar, asegúrate de tener:

- [ ] Cuenta de Google
- [ ] PDFs de facturas (mínimo 10)
- [ ] JSONs anotados (uno por PDF)
- [ ] Notebook `COLAB_ENTRENAMIENTO_LAYOUTLMV3.ipynb`
- [ ] Scripts del proyecto (en GitHub o Drive)
- [ ] 1-2 horas de tiempo libre

---

¡Estás listo para entrenar tu modelo! 🎉

Si tienes problemas, revisa la sección de **Troubleshooting** o verifica que hayas seguido todos los pasos.
