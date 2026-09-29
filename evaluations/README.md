# Suite de Validación Cuantitativa de Tesis (Objetivo 4)

Esta carpeta contiene la infraestructura de pruebas, scripts de evaluación y cálculo de métricas formales para validar el sistema y su arquitectura en el marco de la tesis.

---

## Estructura de la Suite

```text
evaluations/
├── README.md                                  <- Este documento
├── shared/
│   ├── db_sample_extractor.py                 <- Extracción asíncrona de cuestionarios y chunks desde PostgreSQL/Supabase
│   └── metrics_engine.py                      <- Cálculo de Cohen's Kappa, Macro F1, Matriz de Confusión y Faithfulness
├── indicator_4.1_4.2_faithfulness/
│   ├── evaluate_rag_faithfulness.py           <- Evaluación de Fidelidad Semántica y Alucinación
│   └── reports/                               <- Reportes generados en Markdown y JSON
├── indicator_4.3_bloom_alignment/
│   ├── evaluate_bloom_concordance.py          <- Auditoría de concordancia cognitiva de Bloom
│   ├── bloom_pedagogical_evaluator.py         <- Juez evaluador ciego con rúbrica de Bloom
│   └── reports/                               <- Reportes generados en Markdown y JSON
└── indicator_4.4_4.5_4.6_performance_resources/
    ├── input_documents/                       <- Depósito para: 1 PDF, 1 DOCX y 1 PPTX
    │   └── README.md
    ├── benchmark_multiformat.py               <- Profiling de tiempo, Working Set RAM y validación de esquema
    └── reports/                               <- Reportes generados en Markdown y JSON
```

---

## ¿Cómo ejecutar cada Indicador?

### 1. Indicador 4.1 y 4.2: Fidelidad Semántica y Tasa de Alucinación
Extrae los cuestionarios existentes en la base de datos de Supabase, identifica sus chunks de referencia y audita afirmación por afirmación:
```bash
python evaluations/indicator_4.1_4.2_faithfulness/evaluate_rag_faithfulness.py
```
* **Métrica principal:** % de Fidelidad Semántica ($\ge 85\%$) y % de Alucinación ($\le 15\%$).
* **Salida:** Reporte Markdown y JSON guardado en `indicator_4.1_4.2_faithfulness/reports/`.

---

### 2. Indicador 4.3: Concordancia con la Taxonomía de Bloom
Audita una muestra de preguntas en los 5 niveles cognitivos (`remember`, `understand`, `apply`, `analyze`, `evaluate`) con un juez pedagógico ciego.

**Modo Live (Generación fresca en memoria sin guardar en BD):**
* **Escala compacta ($\le 5$ reactivos/nivel = hasta 25 preguntas):** Utiliza automáticamente el resumen conceptual de BDD/Gherkin.
  ```bash
  python evaluations/indicator_4.3_bloom_alignment/evaluate_bloom_concordance.py --live --samples-per-level 5
  ```
* **Escala amplia ($> 5$ reactivos/nivel = 50 a 100+ preguntas):** Detecta la escala y carga automáticamente el material curricular completo [Resource.md](file:///c:/Users/USER/Documents/GitHub/TP-Backend/evaluations/indicator_4.3_bloom_alignment/Resource.md) (21 KB, CMMI y Métricas de Calidad) para prevenir el agotamiento de contexto:
  ```bash
  python evaluations/indicator_4.3_bloom_alignment/evaluate_bloom_concordance.py --live --samples-per-level 20 --batch-size 20
  ```
* **Archivo personalizado opcional:** Puedes forzar cualquier material con `--context-file ruta/a/archivo.md`.
* **Métricas principales:**
  * **Macro F1-Score:** Meta $\ge 0.75$ (Tratamiento equitativo de niveles superiores e inferiores).
  * **Matriz de Confusión ($5 \times 5$):** Tabla de contingencia completa.
* **Salida:** Reporte Markdown y JSON guardado en `indicator_4.3_bloom_alignment/reports/`.

---

### 3. Indicadores 4.4, 4.5 y 4.6: Eficiencia de Recursos y Rendimiento Multiformato
1. Deposita tus 3 archivos de prueba (1 PDF, 1 DOCX y 1 PPTX) dentro de la carpeta:
   `evaluations/indicator_4.4_4.5_4.6_performance_resources/input_documents/`
2. Ejecuta el benchmark:
```bash
python evaluations/indicator_4.4_4.5_4.6_performance_resources/benchmark_multiformat.py
```
* **Métricas principales:**
  * **Pico de Memoria Física (Working Set):** Meta $\le 350.0$ MB.
  * **Adherencia a Esquema Pydantic:** Meta $100\%$ (Zero-failure rate).
  * **Tiempo total por etapa:** Latencia desglosada por formato.
* **Salida:** Reporte comparativo en Markdown y JSON guardado en `indicator_4.4_4.5_4.6_performance_resources/reports/`.
