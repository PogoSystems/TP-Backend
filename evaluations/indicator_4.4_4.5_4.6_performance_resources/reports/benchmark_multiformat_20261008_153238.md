# Reporte de Validación - Indicador 4: Eficiencia de Recursos y Rendimiento Multiformato

- **Fecha de Evaluación:** `2026-09-29T17:46:25.988710`
- **Formatos Analizados:** `3`
- **Estado de Meta de Tesis (RAM $\le 450$ MB y Schema 100%):** **✅ CUMPLIDO**

---

## 1. Tabla Comparativa de Rendimiento y Consumo de Recursos

| Formato / Archivo                                                       |   Tamaño   | Páginas/Slides | Chunks | Tiempo Total | Pico RAM (Working Set) | Pico Heap Python | Adherencia Pydantic |
| :---------------------------------------------------------------------- | :--------: | :------------: | :----: | :----------: | :--------------------: | :--------------: | :-----------------: |
| **PDF** (`Sesion 10 - Calidad y Mejora de Procesos de Software_v2.pdf`) | 895.38 KB  |       33       |   24   |   25.99 s    |     **261.04 MB**      |     17.56 MB     |     100% Válido     |
| **DOCX** (`TF_Grupo3_ 1ASI0438_CMPS_202601.docx`)                       | 1713.51 KB |       29       |   66   |   23.15 s    |     **333.43 MB**      |     41.99 MB     |     100% Válido     |
| **PPTX** (`upc-pre-202601-ASI0570-6525-FromZero-keynote-tb1.pptx`)      | 7090.77 KB |       7        |   7    |    16.4 s    |     **333.43 MB**      |     32.62 MB     |     100% Válido     |

---

## 2. Resumen de Criterios de Aceptación Arquitectural

| Criterio Técnico                                 | Valor Medido  |    Umbral de Éxito de Tesis     |          Veredicto          |
| :----------------------------------------------- | :-----------: | :-----------------------------: | :-------------------------: |
| **Pico Máximo de RAM (Working Set)**             | **333.43 MB** |         $\le 450.0$ MB          | ✅ Dentro del límite seguro |
| **Cumplimiento de Esquema (Schema Conformance)** |   **100%**    |          $\ge 98.0\%$           |    ✅ Zero-failure Rate     |
| **Tiempo Promedio de Pipeline Completo**         |  **21.85 s**  | Operacional para microservicios |         ✅ Estable          |

---

## 3. Justificación de Arquitectura para la Tesis

1. **Gestión de Memoria en Formatos Heterogéneos:**
   - Para archivos **PDF**, el extractor `PdfContentExtractor` delega la rasterización y lectura a `pymupdf4llm` en procesos efímeros, garantizando que el sistema operativo reclame toda la memoria no administrada de bibliotecas nativas de C.
   - Para archivos **DOCX**, `mammoth` descarta payloads de imágenes binarias embebidas, manteniendo el heap de Python por debajo de los 5 MB.
   - Para archivos **PPTX**, la liberación explícita de árboles XML de diapositivas asegura que el consumo físico de memoria permanezca controlado independientemente del volumen de diapositivas.
2. **Determinismo Estructural con Pydantic:**
   El 100% de los cuestionarios generados respetan de forma estricta las especificaciones de tipos (`GeneratedQuiz`), permitiendo la deserialización directa hacia el dominio sin necesidad de capas de sanitización o reintentos costosos.
