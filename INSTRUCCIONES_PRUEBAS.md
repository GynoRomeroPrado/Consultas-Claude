# 📋 Instrucciones para Pruebas con Datos Reales

## 📁 Estructura de Archivos Esperada

He preparado el sistema para recibir tus archivos. Por favor, sube los PDFs y JSONs en la siguiente estructura:

### Opción 1: Estructura Separada (Recomendada)

```
Consultas-Claude/
└── datos_extraidos_de_Originales/
    ├── pdfs/
    │   ├── documento1.pdf
    │   ├── documento2.pdf
    │   └── documento3.pdf
    └── anotaciones/
        ├── documento1.json
        ├── documento2.json
        └── documento3.json
```

### Opción 2: Estructura Simple

```
Consultas-Claude/
└── datos_extraidos_de_Originales/
    ├── documento1.pdf
    ├── documento1.json
    ├── documento2.pdf
    ├── documento2.json
    ├── documento3.pdf
    └── documento3.json
```

**IMPORTANTE**: Los nombres de los archivos PDF y JSON deben coincidir (sin la extensión).

---

## 🚀 Ejecutar las Pruebas

Una vez que hayas subido los archivos:

### 1. Ejecutar Script de Pruebas Automatizado

```bash
python test_real_data.py
```

Este script automáticamente:
- ✅ Busca todos los pares PDF-JSON
- ✅ Inspecciona la estructura de los JSONs
- ✅ Prueba múltiples estrategias de matching (EXACT, AUTO, FUZZY)
- ✅ Compara resultados y recomienda la mejor estrategia
- ✅ Genera reportes detallados
- ✅ Guarda los resultados en `output/pruebas/`

### 2. Prueba Manual con un Solo Documento

```bash
# Básico
python extract_coordinates.py datos_extraidos_de_Originales/pdfs/documento1.pdf \
    -o output/manual/documento1.json

# Con fuzzy matching
python extract_coordinates.py datos_extraidos_de_Originales/pdfs/documento1.pdf \
    -o output/manual/documento1.json --fuzzy --threshold 75 -v

# Exportar a LayoutLM
python extract_coordinates.py datos_extraidos_de_Originales/pdfs/documento1.pdf \
    -o output/manual/documento1_layoutlm.json --format layoutlm
```

### 3. Procesamiento por Lotes

```bash
python extract_coordinates.py \
    --batch datos_extraidos_de_Originales/ \
    output/batch/
```

---

## 📊 Qué Esperar

### El script de pruebas mostrará:

1. **Búsqueda de Archivos**
   ```
   🔍 Buscando archivos en: datos_extraidos_de_Originales/
   Encontrados 5 archivos PDF
     ✓ Emparejado: documento1.pdf <-> documento1.json
     ✓ Emparejado: documento2.pdf <-> documento2.json
   ```

2. **Inspección del JSON**
   ```
   Estructura del JSON: documento1.json
   Tipo: Diccionario con 25 campos
   Campos principales:
     - nombre: Juan Pérez
     - fecha: 2024-01-15
     - total: 1,234.56
   ```

3. **Resultados por Estrategia**
   ```
   📊 RESULTADOS - EXACT
   ================================================================================
     Total de campos:        25
     Campos encontrados:     18
     Campos no encontrados:  7
     Tasa de éxito:          72.0%
     Confianza promedio:     1.0000

     Tipos de matching:
       - exact: 18

   📊 RESULTADOS - FUZZY (threshold=80)
   ================================================================================
     Total de campos:        25
     Campos encontrados:     22
     Campos no encontrados:  3
     Tasa de éxito:          88.0%
     Confianza promedio:     0.9234

     Tipos de matching:
       - exact: 18
       - fuzzy: 4
   ```

4. **Comparación de Estrategias**
   ```
   RESUMEN COMPARATIVO
   ================================================================================
   Estrategia           Threshold    Match Rate      Avg Confidence
   --------------------------------------------------------------------------------
   exact                100.0        72.0%           1.0000
   auto                 80.0         88.0%           0.9234
   fuzzy                80.0         88.0%           0.9120
   fuzzy                70.0         92.0%           0.8845

   🏆 MEJOR ESTRATEGIA: fuzzy (threshold=70.0)
      Match rate: 92.0%
      Avg confidence: 0.8845
   ```

5. **Ejemplos de Matches**
   ```
   📝 EJEMPLOS DE MATCHES:
   ================================================================================
     [1] nombre
         Texto encontrado: 'Juan Pérez García'
         Página: 0, Bbox: (100.5, 200.3, 250.8, 220.1)
         Confianza: 1.00, Tipo: exact

     [2] fecha_nacimiento
         Texto encontrado: '15/03/1985'
         Página: 0, Bbox: (300.2, 200.5, 380.7, 220.3)
         Confianza: 1.00, Tipo: exact
   ```

---

## 🔧 Solución de Problemas Comunes

### Problema 1: "No se encontraron pares PDF-JSON"

**Causa**: Los nombres no coinciden o están en ubicación incorrecta.

**Solución**:
```bash
# Ver qué archivos tienes
ls -la datos_extraidos_de_Originales/

# Si los nombres no coinciden, renombra:
mv archivo.json nombre_correcto.json
```

### Problema 2: "Tasa de éxito muy baja (< 50%)"

**Causa**: El JSON puede tener formato diferente al esperado.

**Solución**:
1. Inspecciona el JSON manualmente:
   ```bash
   cat datos_extraidos_de_Originales/anotaciones/documento1.json | python -m json.tool
   ```

2. Si el JSON tiene estructura anidada especial, ajusta en el código:
   ```python
   # En test_real_data.py, modificar:
   config = PipelineConfig(
       flatten_json=True,  # Para JSONs anidados
       json_separator=".",
       matcher=MatcherConfig(
           strategy=MatchStrategy.FUZZY,
           fuzzy_threshold=70.0  # Bajar threshold si hay errores OCR
       )
   )
   ```

### Problema 3: "Algunos campos no se encuentran"

**Causas posibles**:
- El texto en el PDF tiene errores de OCR
- El texto está en múltiples líneas
- El texto tiene formato especial

**Soluciones**:
```bash
# 1. Usar fuzzy matching más permisivo
python extract_coordinates.py documento.pdf -o output.json --fuzzy --threshold 65 -v

# 2. Ver qué texto hay realmente en el PDF
python -c "
import fitz
doc = fitz.open('datos_extraidos_de_Originales/pdfs/documento1.pdf')
print(doc[0].get_text())
"
```

### Problema 4: "El JSON tiene formato diferente"

Si el JSON tiene estructura como:
```json
{
  "annotations": [
    {"field": "nombre", "value": "Juan"},
    {"field": "edad", "value": "30"}
  ]
}
```

Necesitarás adaptar el parser. Avísame y ajusto el código.

---

## 📝 Información que Necesito

Cuando ejecutes las pruebas, por favor compárteme:

1. **Salida completa del script de pruebas**
2. **Ejemplo de un JSON** (puedes pegar el contenido aquí)
3. **Estadísticas obtenidas**: Match rate, confidence, etc.
4. **Errores específicos** que veas

Con esta información podré:
- ✅ Ajustar el sistema para tu formato específico de JSON
- ✅ Mejorar el matching para tus documentos
- ✅ Optimizar los parámetros
- ✅ Corregir cualquier error

---

## 🎯 Formatos de JSON Soportados

El sistema ya soporta varios formatos:

### Formato 1: Diccionario Simple
```json
{
  "nombre": "Juan Pérez",
  "edad": "30",
  "ciudad": "Madrid"
}
```

### Formato 2: Diccionario Anidado (se aplana automáticamente)
```json
{
  "datos_personales": {
    "nombre": "Juan Pérez",
    "edad": "30"
  },
  "direccion": {
    "calle": "Main St",
    "ciudad": "Madrid"
  }
}
```
Se convierte en:
```json
{
  "datos_personales.nombre": "Juan Pérez",
  "datos_personales.edad": "30",
  "direccion.calle": "Main St",
  "direccion.ciudad": "Madrid"
}
```

### Formato 3: Con Arrays
```json
{
  "nombre": "Juan",
  "telefonos": ["600123456", "911234567"]
}
```

Si tienes un formato diferente, ¡avísame para adaptarlo!

---

## 📞 Siguiente Paso

**Por favor, ejecuta:**

```bash
python test_real_data.py
```

Y comparte la salida completa. Con eso podré identificar y corregir cualquier error específico de tu caso de uso.
