================================================================================
INSTRUCCIONES PARA SUBIR ARCHIVOS
================================================================================

Por favor, sube tus archivos en la siguiente estructura:

📁 datos_extraidos_de_Originales/
   📁 pdfs/
      📄 documento1.pdf
      📄 documento2.pdf
      📄 documento3.pdf
      ...
   📁 anotaciones/
      📝 documento1.json
      📝 documento2.json
      📝 documento3.json
      ...

IMPORTANTE:
- Los nombres de PDF y JSON deben coincidir (sin la extensión)
- Ejemplo: "factura_001.pdf" debe tener "factura_001.json"

================================================================================
FORMATO ESPERADO DEL JSON
================================================================================

El JSON debe contener los campos que quieres buscar en el PDF:

{
  "nombre_completo": "Juan Pérez García",
  "documento_identidad": "12345678-A",
  "fecha_nacimiento": "15/03/1985",
  "direccion": "Avenida Principal 123",
  "ciudad": "Madrid",
  "codigo_postal": "28001",
  "telefono": "+34 600 123 456",
  "email": "juan.perez@email.com"
}

También soporta JSONs anidados:

{
  "datos_personales": {
    "nombre": "Juan Pérez",
    "edad": "30"
  },
  "datos_laborales": {
    "empresa": "Tech Solutions",
    "cargo": "Desarrollador"
  }
}

================================================================================
DESPUÉS DE SUBIR LOS ARCHIVOS
================================================================================

1. Verifica que los archivos se subieron correctamente:

   python verificar_archivos.py

2. Ejecuta las pruebas automatizadas:

   python test_real_data.py

3. O procesa manualmente un documento específico:

   python extract_coordinates.py datos_extraidos_de_Originales/pdfs/documento1.pdf -o output.json -v

================================================================================
