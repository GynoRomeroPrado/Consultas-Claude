# PDF-JSON Coordinate Extraction System

Sistema avanzado para extraer coordenadas (bounding boxes) de campos en archivos PDF usando archivos JSON como referencia. Ideal para crear datasets de entrenamiento para modelos de reconocimiento de texto en documentos (LayoutLM, BERT para documentos, etc.).

## 🎯 Características

- ✅ **Múltiples estrategias de matching**: Exact, Fuzzy, Multiline
- ✅ **Manejo inteligente de texto multilínea**: Detección automática
- ✅ **Fuzzy matching avanzado**: RapidFuzz con múltiples algoritmos
- ✅ **Normalización de texto robusta**: Unicode, espacios, caracteres especiales
- ✅ **Múltiples formatos de exportación**: LayoutLM, COCO, Pascal VOC, YOLO, JSON, CSV
- ✅ **Procesamiento por lotes**: Procesa múltiples documentos
- ✅ **Configuración flexible**: Sistema de configuración modular
- ✅ **Métricas detalladas**: Confidence scores, estadísticas de matching

## 🏗️ Arquitectura

```
src/
├── extractors/          # Extracción de datos
│   ├── pdf_extractor.py    # PyMuPDF para PDFs
│   └── json_parser.py      # Parser de JSON
├── matchers/            # Algoritmos de matching
│   ├── exact_matcher.py    # Matching exacto
│   ├── fuzzy_matcher.py    # Matching difuso (RapidFuzz)
│   └── multiline_matcher.py # Texto multilínea
├── normalizers/         # Normalización
│   ├── text_normalizer.py   # Normalización de texto
│   └── coord_normalizer.py  # Normalización de coordenadas
├── exporters/           # Exportación de resultados
│   ├── layoutlm_exporter.py # Formato LayoutLM
│   ├── coco_exporter.py     # Formato COCO
│   └── custom_exporter.py   # Formatos personalizados
└── core/                # Pipeline principal
    ├── pipeline.py          # Orquestador principal
    └── config.py            # Configuración
```

## 📦 Instalación

```bash
# Clonar el repositorio
git clone <repository-url>
cd Consultas-Claude

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias principales

- **PyMuPDF (fitz)**: Extracción de PDF (40x más rápido que alternativas)
- **RapidFuzz**: Fuzzy matching (40% más rápido que FuzzyWuzzy)
- **NumPy/Pandas**: Manipulación de datos
- **Pillow**: Procesamiento de imágenes

## 🚀 Uso Rápido

### Ejemplo Básico

```python
from src.core.pipeline import CoordinateExtractionPipeline

# Crear pipeline
pipeline = CoordinateExtractionPipeline()

# Procesar PDF-JSON
result = pipeline.process(
    pdf_path="documento.pdf",
    json_path="documento.json",
    output_path="output/resultado.json"
)

# Ver estadísticas
print(f"Match rate: {result['statistics']['match_rate']}%")
```

### Configuración Personalizada

```python
from src.core.config import PipelineConfig, MatchStrategy, ExportFormat

# Configurar pipeline
config = PipelineConfig(
    matcher=MatcherConfig(
        strategy=MatchStrategy.FUZZY,
        fuzzy_threshold=80.0
    ),
    exporter=ExporterConfig(
        format=ExportFormat.LAYOUTLM,
        target_scale=1000
    )
)

pipeline = CoordinateExtractionPipeline(config=config)
```

### Procesamiento por Lotes

```python
# Lista de pares PDF-JSON
pairs = [
    ("doc1.pdf", "doc1.json"),
    ("doc2.pdf", "doc2.json"),
    ("doc3.pdf", "doc3.json")
]

# Procesar todos
results = pipeline.batch_process(pairs, output_dir="output/batch")
```

## 📄 Formatos de Entrada

### JSON esperado

```json
{
  "nombre": "Juan Pérez",
  "fecha": "2024-01-15",
  "total": "1,234.56",
  "direccion": {
    "calle": "Av. Principal 123",
    "ciudad": "Ciudad"
  }
}
```

El sistema:
- ✅ Aplana automáticamente JSONs anidados
- ✅ Convierte valores a strings
- ✅ Maneja arrays y objetos complejos

## 📊 Formatos de Exportación

### 1. LayoutLM (0-1000 scale)

```json
{
  "format": "layoutlm",
  "scale": 1000,
  "pages": [{
    "page": 0,
    "annotations": [{
      "text": "Juan Pérez",
      "label": "nombre",
      "bbox": [100, 200, 300, 250],
      "confidence": 1.0
    }]
  }]
}
```

### 2. COCO Format

```json
{
  "images": [...],
  "annotations": [{
    "id": 1,
    "image_id": 1,
    "category_id": 1,
    "bbox": [x, y, width, height],
    "area": 5000
  }],
  "categories": [...]
}
```

### 3. CSV

```csv
field_name,text,x0,y0,x1,y1,page,confidence
nombre,Juan Pérez,100,200,300,250,0,1.0
```

### 4. Pascal VOC (XML)

```xml
<annotation>
  <object>
    <name>nombre</name>
    <bndbox>
      <xmin>100</xmin>
      <ymin>200</ymin>
      <xmax>300</xmax>
      <ymax>250</ymax>
    </bndbox>
  </object>
</annotation>
```

### 5. YOLO

```
0 0.5 0.3 0.2 0.1
# class_id center_x center_y width height (normalized)
```

## 🎛️ Configuración Avanzada

### Estrategias de Matching

```python
# EXACT: Solo coincidencias exactas (más rápido)
MatchStrategy.EXACT

# FUZZY: Permite errores de OCR, variaciones
MatchStrategy.FUZZY

# AUTO: Intenta EXACT primero, luego FUZZY (recomendado)
MatchStrategy.AUTO

# MULTILINE: Para texto en múltiples líneas
MatchStrategy.MULTILINE
```

### Ajustar Fuzzy Threshold

```python
config = PipelineConfig(
    matcher=MatcherConfig(
        fuzzy_threshold=70.0  # 0-100, menor = más permisivo
    )
)
```

### Normalización de Texto

```python
from src.normalizers.text_normalizer import TextNormalizer

normalizer = TextNormalizer(
    unicode_form="NFKC",           # Normalización Unicode
    lowercase=True,                 # Convertir a minúsculas
    remove_extra_whitespace=True,   # Normalizar espacios
    remove_punctuation=False        # Conservar puntuación
)
```

## 🔧 Uso Avanzado

### 1. Componentes Individuales

```python
from src.extractors.pdf_extractor import PDFExtractor

# Extraer palabras con coordenadas
extractor = PDFExtractor()
words = extractor.extract_words("documento.pdf")

# Buscar texto específico
matches = extractor.search_text("documento.pdf", "texto a buscar")
```

### 2. Matching Personalizado

```python
from src.matchers.fuzzy_matcher import MultiStrategyMatcher

matcher = MultiStrategyMatcher()
match = matcher.find_best_match("texto", words_data)

print(f"Confianza: {match.confidence}")
print(f"Bbox: {match.bbox}")
```

### 3. Exportación Personalizada

```python
from src.exporters.custom_exporter import CustomExporter

exporter = CustomExporter()

# JSON
exporter.export_json(matches, field_names, "output.json")

# CSV
exporter.export_csv(matches, field_names, "output.csv")

# Pascal VOC
exporter.export_pascal_voc(matches, field_names, "doc.pdf", "output_dir/")
```

## 📊 Resultados y Estadísticas

```python
result = pipeline.process(pdf_path, json_path, output_path)

stats = result['statistics']
# {
#   'total_fields': 10,
#   'matched_fields': 8,
#   'match_rate': 80.0,
#   'average_confidence': 0.95,
#   'match_types': {
#     'exact': 6,
#     'fuzzy': 2
#   },
#   'pages_with_matches': 2
# }
```

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/

# Con cobertura
pytest --cov=src tests/
```

## 🤝 Casos de Uso

### 1. Entrenamiento de LayoutLM

```python
config = PipelineConfig(
    exporter=ExporterConfig(
        format=ExportFormat.LAYOUTLM,
        target_scale=1000
    )
)
pipeline = CoordinateExtractionPipeline(config=config)
```

### 2. Dataset para Object Detection (YOLO/COCO)

```python
config = PipelineConfig(
    exporter=ExporterConfig(format=ExportFormat.COCO)
)
```

### 3. OCR con Errores

```python
config = PipelineConfig(
    matcher=MatcherConfig(
        strategy=MatchStrategy.FUZZY,
        fuzzy_threshold=70.0
    )
)
```

## 🎯 Mejores Prácticas

### 1. Texto Multilínea

El sistema maneja automáticamente texto en múltiples líneas usando PyMuPDF:

```python
# Automático con strategy=AUTO
config = PipelineConfig(
    matcher=MatcherConfig(
        strategy=MatchStrategy.AUTO,
        use_multiline=True
    )
)
```

### 2. Duplicados

Para manejar texto duplicado en el PDF:

```python
config = PipelineConfig(
    matcher=MatcherConfig(
        prefer_first_match=True  # Usa la primera aparición
    )
)
```

### 3. Performance

```python
# Para mejor performance
config = PipelineConfig(
    matcher=MatcherConfig(
        strategy=MatchStrategy.EXACT  # Más rápido
    ),
    verbose=False  # Sin logs detallados
)
```

## 🐛 Troubleshooting

### Problema: No encuentra matches

**Solución 1**: Usar fuzzy matching
```python
config.matcher.strategy = MatchStrategy.FUZZY
config.matcher.fuzzy_threshold = 70.0
```

**Solución 2**: Verificar normalización
```python
config.normalizer.lowercase = True
config.normalizer.remove_extra_whitespace = True
```

### Problema: Coordenadas incorrectas

**Verificar**:
- El PDF no sea escaneado (usar OCR primero)
- Las páginas tengan las dimensiones correctas
- Los bounding boxes estén en el formato correcto

### Problema: Texto multilínea no detectado

**Solución**:
```python
config.matcher.use_multiline = True
config.matcher.strategy = MatchStrategy.MULTILINE
```

## 📚 Bibliografía y Referencias

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [RapidFuzz Documentation](https://github.com/rapidfuzz/RapidFuzz)
- [LayoutLM Paper](https://arxiv.org/abs/1912.13318)
- [COCO Format](https://cocodataset.org/#format-data)

## 🔄 Actualizaciones Futuras

- [ ] Soporte para PDFs escaneados (OCR integrado)
- [ ] Visualización de resultados
- [ ] API REST
- [ ] CLI mejorada
- [ ] Soporte para más formatos de exportación
- [ ] Cache de resultados
- [ ] Procesamiento paralelo

## 📝 Licencia

[Especificar licencia]

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📧 Contacto

[Especificar información de contacto]

---

**Desarrollado con ❤️ usando Python, PyMuPDF y RapidFuzz**
