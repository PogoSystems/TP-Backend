# Subcarpeta de Documentos de Entrada para Benchmarking (Indicador 4)

Deposita en esta carpeta los **3 documentos académicos** para ejecutar el benchmarking comparativo multiformato:

1. **Documento PDF:** Cualquier archivo con extensión `.pdf` (ej. `muestra.pdf` o diapositivas/lecturas en PDF).
2. **Documento Word:** Cualquier archivo con extensión `.docx` (ej. `guia_estudio.docx` o documento con encabezados).
3. **Presentación PowerPoint:** Cualquier archivo con extensión `.pptx` (ej. `clase_semana1.pptx`).

---

### ¿Cómo los procesa el sistema?
* **PDF:** Extraído con `PdfContentExtractor` (`pymupdf4llm` y `fitz`) optimizado en subproceso efímero para evitar retención de memoria en C.
* **DOCX:** Extraído con `DocxContentExtractor` (`mammoth`) omitiendo imágenes pesadas.
* **PPTX:** Extraído con `PptxContentExtractor` (`python-pptx`) estructurando diapositiva por diapositiva.

Una vez depositados, ejecuta:
```bash
python evaluations/indicator_4_performance_resources/benchmark_multiformat.py
```
El script detectará automáticamente los 3 archivos, ejecutará el pipeline completo en cada uno y generará una tabla comparativa con los picos de memoria RAM (Working Set), tiempos de respuesta y cumplimiento de esquema Pydantic.
