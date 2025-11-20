# Sistema de Procesamiento de Facturas Peruanas con Donut

Sistema end-to-end para extracción automática de datos de facturas peruanas usando el modelo **Donut (Swin + BART)**, optimizado para impresiones matriciales y papel autocopiativo.

## 🎯 Características Principales

### Arquitectura Core
- **Modelo Donut**: Arquitectura libre de OCR externo que elimina propagación de errores
- **Alta Resolución**: Soporta imágenes de hasta 2560x1920 píxeles para lectura precisa de texto legal pequeño
- **Preprocesamiento Avanzado**: Operaciones morfológicas para fusionar puntos de impresión matricial
- **Validación SUNAT**: Verificación automática de RUCs con algoritmo de Módulo 11

### Pipeline Completo
1. **Preprocesamiento**: Morfología (Closing) + Deskewing
2. **Augmentación**: Augraphy para generar 3-5 variantes sintéticas por factura
3. **Entrenamiento Multi-Fase**: Sintético → Mixto → Real
4. **Optimización**: Exportación ONNX + Cuantización INT8 para despliegue en CPU

## 📊 Tabla Técnica de Componentes

| Componente | Herramienta | Impacto |
|------------|-------------|---------|
| **Arquitectura Core** | Donut (Swin + BART) | Elimina errores de OCR en impresiones matriciales |
| **Preprocesamiento** | Morfología (Closing) | Fusiona puntos dispersos en glifos sólidos |
| **Alineación** | Proyección de Perfil | Corrige rotación del papel escaneado |
| **Datos (Dataset)** | Augraphy Pipeline | Previene sobreajuste con 5k muestras augmentadas |
| **Entrenamiento** | Resolución 2560px | Lectura precisa de texto pequeño y tablas densas |
| **Optimización** | ONNX + INT8 | Reduce latencia de segundos a milisegundos en CPU |
| **Validación** | Lógica SUNAT (Módulo 11) | Garantiza RUCs matemáticamente válidos |

## 🚀 Inicio Rápido

### Instalación

```bash
# Clonar repositorio
git clone <url-del-repo>
cd Consultas-Claude

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Uso Básico

#### 1. Preprocesar Imágenes

```python
from src.preprocessing.pipeline import create_high_resolution_pipeline

# Crear pipeline
pipeline = create_high_resolution_pipeline(
    target_width=1920,
    target_height=2560
)

# Procesar imagen
processed = pipeline.process(image)
```

#### 2. Augmentar Dataset

```python
from src.augmentation.augraphy_pipeline import InvoiceAugmentationPipeline

# Crear pipeline de augmentación
aug_pipeline = InvoiceAugmentationPipeline(intensity="medium")

# Augmentar dataset completo
stats = aug_pipeline.augment_dataset(
    input_dir="./data/raw",
    output_dir="./data/augmented",
    variants_per_image=3
)
```

#### 3. Entrenar Modelo

```python
from src.model.donut_config import create_high_resolution_config, create_training_config
from src.model.trainer import create_trainer

# Configurar modelo
model_config = create_high_resolution_config(width=1920, height=2560)
training_config = create_training_config(num_epochs=30, batch_size=2)

# Crear y entrenar
trainer = create_trainer(model_config, training_config)
metrics = trainer.train_all_phases(
    synthetic_dataset=synthetic_data,
    real_dataset=real_data,
    val_dataset=val_data
)
```

#### 4. Validar Resultados

```python
from src.validation.sunat_validator import validate_invoice

# Validar factura extraída
invoice_data = {
    "ruc_e": "20123456789",
    "sub": 1000.0,
    "igv": 180.0,
    "tot": 1180.0
}

results = validate_invoice(invoice_data)
print(f"Válida: {results['valid']}")
print(f"Errores: {results['errors']}")
```

#### 5. Exportar a ONNX

```python
from src.optimization.onnx_exporter import export_model_to_onnx

# Exportar y cuantizar
paths = export_model_to_onnx(
    model_path="./checkpoints/final_model",
    output_dir="./onnx_models",
    quantize=True
)
```

## 📁 Estructura del Proyecto

```
Consultas-Claude/
├── src/
│   ├── preprocessing/        # Morfología y deskewing
│   │   ├── morphology.py
│   │   ├── deskewing.py
│   │   └── pipeline.py
│   ├── augmentation/         # Pipeline Augraphy
│   │   └── augraphy_pipeline.py
│   ├── model/               # Configuración y entrenamiento Donut
│   │   ├── donut_config.py
│   │   └── trainer.py
│   ├── optimization/        # Exportación ONNX
│   │   └── onnx_exporter.py
│   └── validation/          # Validación SUNAT
│       └── sunat_validator.py
├── data/
│   ├── raw/                 # Facturas originales
│   ├── augmented/           # Variantes sintéticas
│   └── processed/           # Imágenes preprocesadas
├── configs/                 # Archivos de configuración YAML
├── scripts/                 # Scripts de ejecución
├── notebooks/               # Notebooks de experimentación
├── tests/                   # Tests unitarios
├── requirements.txt         # Dependencias Python
└── README.md
```

## 🗺️ Hoja de Ruta (Roadmap)

### **Semana 1-2: Preparación del Entorno de Datos**
- [ ] Instalar Augraphy y diseñar pipeline de degradación
- [ ] Aumentar dataset de 5,000 a 15,000-25,000 imágenes (3-5 variantes cada una)
- [ ] Validar calidad de imágenes sintéticas

### **Semana 2: Implementación del Preprocesamiento**
- [x] Desarrollar script de morfología (Closing)
- [x] Implementar algoritmo de deskewing
- [x] Crear pipeline integrado

### **Semana 3: Configuración del Modelo Donut**
- [x] Modificar DonutSwinConfig para resolución 1920x2560
- [x] Activar interpolación bicúbica de embeddings posicionales
- [x] Optimizar esquema JSON con claves cortas

### **Semana 4-6: Entrenamiento Estratégico**
- [x] Implementar entrenamiento multi-fase
- [ ] Fase 1: Entrenar con imágenes sintéticas (15 epochs)
- [ ] Fase 2: Fine-tuning con datos mixtos (10 epochs)
- [ ] Fase 3: Ajuste final con datos reales (5 epochs)

### **Semana 7: Optimización para Despliegue**
- [x] Exportar a formato ONNX (Encoder + Decoder separados)
- [x] Aplicar cuantización INT8
- [ ] Benchmark de rendimiento en CPU

## 🔬 Detalles Técnicos

### Preprocesamiento

**Operación de Cierre Morfológico**: `(A ⊕ B) ⊖ B`

```python
# Kernel rectangular 3x3
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

# Cierre morfológico
closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
```

### Validación de RUC (Módulo 11)

```python
def validate_ruc(ruc: str) -> bool:
    factores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(ruc[i]) * factores[i] for i in range(10))
    digito_verificador = 11 - (suma % 11)
    if digito_verificador == 11:
        digito_verificador = 0
    elif digito_verificador == 10:
        digito_verificador = 1
    return int(ruc[10]) == digito_verificador
```

### Configuración de Alta Resolución

```python
config = DonutModelConfig(
    image_size=[2560, 1920],  # [height, width]
    interpolate_position_embeddings=True,
    position_embedding_type="bicubic"
)
```

## 📊 Rendimiento Esperado

| Métrica | Antes (OCR tradicional) | Después (Donut optimizado) |
|---------|-------------------------|----------------------------|
| **Precisión en texto matricial** | ~60% | ~95% |
| **Latencia (CPU)** | 5-10 segundos | 200-500 ms |
| **Tamaño del modelo** | ~2 GB | ~500 MB (cuantizado) |
| **RUCs válidos** | ~70% (con errores) | ~99% (con validación) |

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/

# Con coverage
pytest --cov=src tests/
```

## 📝 Notas Importantes

### Configuración GPU (Opcional pero Recomendado)

```bash
# Para entrenamiento con GPU
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Memoria Requerida

- **Entrenamiento**: ~16 GB RAM + 8 GB VRAM (GPU)
- **Inferencia**: ~4 GB RAM (CPU) o ~2 GB VRAM (GPU)
- **Inferencia ONNX cuantizada**: ~2 GB RAM (CPU)

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 📧 Contacto

Para preguntas o soporte, por favor abre un issue en GitHub.

---

**Desarrollado para procesamiento eficiente de facturas peruanas con impresión matricial y papel autocopiativo.**
