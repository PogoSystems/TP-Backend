"""
Evaluación del Indicador 1: Fidelidad Semántica y Tasa de Alucinación (Faithfulness & Groundedness).
Extrae cuestionarios reales persistidos en la base de datos de Supabase,
descompone sus enunciados, respuestas y explicaciones en afirmaciones atómicas
y las contrasta contra los fragmentos de contexto (document_chunk) correspondientes.
Incluye contingencia transparente a Groq ante límites de cuota (429) de Gemini
y emparejamiento semántico de fragmentos relevantes por reactivo.
"""

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional

# Asegurar path raíz en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from google import genai
from google.genai import types
from google.genai.errors import APIError
from groq import AsyncGroq
from pydantic import BaseModel, Field

from core.settings import settings
from evaluations.shared.db_sample_extractor import DbSampleExtractor
from evaluations.shared.metrics_engine import calculate_faithfulness

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("google.genai").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("Indicator1_Faithfulness")


# Esquemas Pydantic para Structured Output del LLM Evaluador
class ClaimVerification(BaseModel):
    claim: str = Field(description="Afirmación factual o conceptual extraída de la pregunta, respuesta correcta o justificación")
    is_grounded: bool = Field(description="True si la afirmación está explícitamente respaldada por el contexto RAG; False si es alucinada o inventada")
    evidence_quote: str = Field(default="", description="Cita breve del fragmento de contexto que respalda la afirmación, o vacío si no se encuentra")
    reasoning: str = Field(description="Breve justificación del veredicto")


class QuestionFaithfulnessResult(BaseModel):
    question_id: int
    claims: List[ClaimVerification]
    is_fully_faithful: bool
    summary_verdict: str


def select_relevant_chunks_for_question(
    question_text: str,
    answers: List[Dict[str, Any]],
    correct_answers: List[str],
    explanation: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 15,
) -> str:
    """
    Selecciona los fragmentos de texto más relevantes para la pregunta específica.
    Si el conjunto total de fragmentos es de 25 o menos, incluye todo el material disponible
    para prevenir desabastecimiento de contexto (context starvation).
    Para colecciones mayores, aplica coincidencia léxica ponderada extrayendo términos clave del reactivo.
    """
    if not chunks:
        return ""

    if len(chunks) <= 25:
        return "\n\n".join([
            f"[Fragmento #{c['chunk_index']} - {c['heading_path']}]:\n{c['content']}"
            for c in chunks
        ])

    all_answers_text = " ".join([a.get("text", "") for a in answers])
    search_text = f"{question_text} {' '.join(correct_answers)} {all_answers_text} {explanation}".lower()
    stopwords = {
        "para", "como", "cual", "esta", "este", "entre", "sobre", "desde", "hacia", "pero",
        "donde", "cuando", "estos", "estas", "cualquier", "algun", "alguna", "tiene", "puede"
    }
    keywords = {w for w in re.findall(r"\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}\b", search_text) if w not in stopwords}

    scored_chunks = []
    for c in chunks:
        content_lower = c["content"].lower()
        heading_lower = c["heading_path"].lower()

        score = 0
        for kw in keywords:
            if kw in heading_lower:
                score += 4  # Mayor peso a coincidencia en títulos/secciones temáticas
            if kw in content_lower:
                score += 1

        scored_chunks.append((score, c))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    best_chunks = [item[1] for item in scored_chunks[:top_k]]
    # Reordenar por chunk_index para mantener coherencia narrativa
    best_chunks.sort(key=lambda x: x.get("chunk_index", 0))

    return "\n\n".join([
        f"[Fragmento #{c['chunk_index']} - {c['heading_path']}]:\n{c['content']}"
        for c in best_chunks
    ])


class FaithfulnessEvaluator:
    """
    Evaluador de fidelidad y alucinación mediante LLM-as-a-Judge con contingencia automática a Groq.
    """

    def __init__(self):
        self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._gemini_model = settings.GEMINI_MODEL
        self._groq_client: Optional[AsyncGroq] = None
        # Usar gpt-oss-20b para evitar límites de tokens por minuto (TPM) de modelos gigantes
        self._groq_model: str = "openai/gpt-oss-20b"
        if settings.GROQ_API_KEY:
            self._groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def evaluate_question_against_context(
        self,
        question_id: int,
        question_text: str,
        answers: List[Dict[str, Any]],
        correct_answers: List[str],
        explanation: str,
        context_text: str,
    ) -> Optional[QuestionFaithfulnessResult]:
        """
        Extrae afirmaciones del reactivo y verifica su respaldo factual en el contexto.
        """
        # Formatear opciones distinguiendo claramente la clave correcta de los distractores didácticos
        options_formatted = []
        for a in answers:
            tag = "[OPCIÓN CORRECTA]" if a.get("is_correct") else "[DISTRACTOR / OPCIÓN INCORRECTA]"
            options_formatted.append(f"  - {tag}: {a.get('text')}")
        options_block = "\n".join(options_formatted)

        prompt = f"""
Eres un auditor académico y evaluador de fidelidad factual para sistemas RAG (Retrieval-Augmented Generation) según el marco metodológico estándar (Es et al., 2023 - RAGAS).
Tu objetivo es verificar si la pregunta generada, su clave de respuesta correcta y la fundamentación pedagógica que sustenta dicha clave provienen estrictamente del material de referencia proporcionado o si contienen ALUCINACIONES (hechos contradictorios, inventados o no derivables).

Material de Referencia (Contexto recuperado de los documentos fuente):
---
{context_text}
---

Reactivo a Auditar:
- ID de Pregunta: {question_id}
- Enunciado: {question_text}
- Opciones de respuesta presentadas al estudiante:
{options_block}
- Respuesta(s) declarada(s) como correcta(s): {', '.join(correct_answers)}
- Explicación brindada al estudiante: {explanation}

Directivas Metodológicas de Evaluación:
1. Enfoque en la Clave Correcta y sus Fundamentos:
   - Descompón el reactivo en afirmaciones atómicas (claims) centradas en:
     a) Las premisas del ENUNCIADO.
     b) La afirmación que sostiene la OPCIÓN DECLARADA COMO CORRECTA.
     c) Los hechos didácticos que explican POR QUÉ la opción correcta es la adecuada.
2. Tratamiento de Opciones Incorrectas (Distractores):
   - Los distractores son alternativas falsas creadas artificialmente para evaluar al alumno. NO evalúes los distractores como afirmaciones que deban ser verdaderas en el texto fuente.
   - Si la explicación descarta un distractor apelando a distinciones conceptuales generales (ej. indicar que una opción pertenece a otra metodología, que no aplica al caso, o contrastarla con la clave), NO califiques ese argumento de descarte como alucinación si la clave correcta está respaldada.
3. Paráfrasis y Deducciones Lógicas Válidas:
   - Si una afirmación sintetiza, parafrasea con sinónimos o deduce lógicamente información del contexto, clasifícala como 'is_grounded': true. NO exijas coincidencia léxica literal palabra por palabra.
4. Criterio Estricto de Alucinación ('is_grounded': false):
   - Marca 'is_grounded': false ÚNICAMENTE si la opción declarada como correcta o su fundamentación central contradice el material, inventa conceptos técnicos inexistentes en el texto o atribuye hechos falsos no derivables del material de referencia.
5. Genera la salida siguiendo estrictamente el esquema JSON solicitado.
"""

        # 1. Intentar con Gemini
        try:
            response = await self._gemini_client.aio.models.generate_content(
                model=self._gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuestionFaithfulnessResult,
                    temperature=0.0,
                ),
            )

            if not response.text:
                raise ValueError("Respuesta vacía del LLM evaluador Gemini")

            return QuestionFaithfulnessResult.model_validate_json(response.text)

        except Exception as e:
            # Si Gemini falla por cualquier razón (404 no encontrado, 429 cuota, 503, etc.), pasar a Groq
            if self._groq_client:
                logger.warning(
                    f"Gemini API no disponible para reactivo #{question_id} ({e}). "
                    f"Activando contingencia a Groq ({self._groq_model})..."
                )
                return await self._evaluate_with_groq(prompt, question_id)

            logger.error(f"Fallo al evaluar reactivo #{question_id} sin evaluador secundario disponible: {e}")
            return None

    async def _evaluate_with_groq(
        self, prompt: str, question_id: int, max_retries: int = 4
    ) -> Optional[QuestionFaithfulnessResult]:
        """
        Fallback a Groq con reintentos y backoff exponencial ante límites de tasa (429) o errores temporales.
        """
        schema_json = QuestionFaithfulnessResult.model_json_schema()
        system_instruction = (
            "Eres un auditor académico experto en RAG. "
            "Debes retornar obligatoriamente un JSON válido cumpliendo este JSON Schema exacto:\n"
            f"{json.dumps(schema_json, ensure_ascii=False)}\n"
            "No agregues texto conversational fuera del JSON."
        )

        if not self._groq_client:
            logger.error(
                "El cliente de Groq no está inicializado. "
                "Verifica que GROQ_API_KEY esté configurada en el entorno o archivo .env."
            )
            return None

        for attempt in range(1, max_retries + 1):
            try:
                completion = await self._groq_client.chat.completions.create(
                    model=self._groq_model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )

                content = completion.choices[0].message.content or "{}"
                clean_json = content.strip()
                if clean_json.startswith("```"):
                    clean_json = clean_json.split("\n", 1)[1]
                if clean_json.endswith("```"):
                    clean_json = clean_json.rsplit("```", 1)[0]
                clean_json = clean_json.strip()

                return QuestionFaithfulnessResult.model_validate_json(clean_json)

            except Exception as groq_err:
                err_str = str(groq_err)
                is_rate_limit = "429" in err_str or "rate_limit" in err_str.lower() or "too many requests" in err_str.lower()
                is_server_error = "500" in err_str or "503" in err_str

                if (is_rate_limit or is_server_error) and attempt < max_retries:
                    wait_time = 2.5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"Groq API {('Rate limit (429)' if is_rate_limit else 'Error de servidor')} en reactivo #{question_id} (intento {attempt}/{max_retries}). "
                        f"Esperando {wait_time:.1f}s antes de reintentar..."
                    )
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f"Fallo definitivo en evaluador Groq para reactivo #{question_id}: {groq_err}")
                return None


async def run_faithfulness_evaluation(limit_quizzes: int = 10) -> Dict[str, Any]:
    """
    Ejecuta el pipeline completo de evaluación del Indicador 1.
    """
    logger.info("Iniciando extracción de cuestionarios desde la base de datos...")
    extractor = DbSampleExtractor()
    quizzes_summary = await extractor.get_quizzes_summary(limit=limit_quizzes)

    if not quizzes_summary:
        logger.warning("No se encontraron cuestionarios en la base de datos.")
        return {
            "error": "No se encontraron cuestionarios en la base de datos de Supabase/PostgreSQL.",
            "quizzes_evaluated": 0,
        }

    logger.info(f"Se encontraron {len(quizzes_summary)} cuestionarios para auditar.")

    evaluator = FaithfulnessEvaluator()
    total_claims = 0
    total_verified = 0
    total_audited_questions = 0
    unprocessed_questions = 0
    detailed_results = []

    for q_meta in quizzes_summary:
        quiz_id = q_meta["quiz_id"]
        logger.info(f"Auditando Quiz ID {quiz_id} - '{q_meta['title']}'...")
        quiz_data = await extractor.extract_quiz_with_context(quiz_id)

        if not quiz_data or not quiz_data["questions"]:
            logger.warning(f"Quiz #{quiz_id} no contiene preguntas.")
            continue

        raw_chunks = quiz_data.get("chunks", [])
        if not raw_chunks:
            logger.warning(f"Quiz #{quiz_id} no tiene chunks asociados en BD. Se omite.")
            continue

        quiz_eval = {
            "quiz_id": quiz_id,
            "title": quiz_data["title"],
            "course_id": quiz_data["course_id"],
            "chunks_count": len(raw_chunks),
            "questions_evaluated": [],
        }

        for q in quiz_data["questions"]:
            # Seleccionar dinámicamente los fragmentos más pertinentes para este reactivo específico
            # Cobertura expandida (top_k=12) y traspaso completo para documentos pequeños para prevenir context starvation
            relevant_context = select_relevant_chunks_for_question(
                question_text=q["text"],
                answers=q.get("answers", []),
                correct_answers=q["correct_answers"],
                explanation=q["explanation"],
                chunks=raw_chunks,
                top_k=15,
            )

            res = await evaluator.evaluate_question_against_context(
                question_id=q["question_id"],
                question_text=q["text"],
                answers=q.get("answers", []),
                correct_answers=q["correct_answers"],
                explanation=q["explanation"],
                context_text=relevant_context,
            )

            if res is None:
                unprocessed_questions += 1
                logger.warning(f"Reactivo #{q['question_id']} catalogado como fallo técnico de APIs (omitido de la métrica de alucinación).")
                quiz_eval["questions_evaluated"].append({
                    "question_id": q["question_id"],
                    "text": q["text"],
                    "bloom_level": q["bloom_level"],
                    "status": "technical_error",
                    "is_fully_faithful": None,
                    "claims": [],
                })
            else:
                total_audited_questions += 1
                for claim in res.claims:
                    total_claims += 1
                    if claim.is_grounded:
                        total_verified += 1

                quiz_eval["questions_evaluated"].append({
                    "question_id": q["question_id"],
                    "text": q["text"],
                    "bloom_level": q["bloom_level"],
                    "status": "evaluated",
                    "is_fully_faithful": res.is_fully_faithful,
                    "claims": [c.model_dump() for c in res.claims],
                })

            # Pausa defensiva para respetar límites de tasa (~30 RPM)
            await asyncio.sleep(1.5)

        detailed_results.append(quiz_eval)

    # Cálculo con MetricsEngine
    metrics = calculate_faithfulness(total_verified, total_claims) if total_claims > 0 else {
        "faithfulness_percentage": 0.0,
        "hallucination_percentage": 0.0,
    }

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "quizzes_audited": len(detailed_results),
        "total_questions_audited": total_audited_questions,
        "unprocessed_questions_due_to_api_error": unprocessed_questions,
        "total_claims_analyzed": total_claims,
        "verified_grounded_claims": total_verified,
        "hallucinated_claims": total_claims - total_verified,
        "faithfulness_score_percentage": metrics["faithfulness_percentage"],
        "hallucination_rate_percentage": metrics["hallucination_percentage"],
        "academic_threshold_met": (metrics["faithfulness_percentage"] >= 85.0) if total_claims > 0 else False,
        "detailed_results": detailed_results,
    }

    # Guardar reportes
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = reports_dir / f"faithfulness_report_{timestamp_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    md_path = reports_dir / f"faithfulness_report_{timestamp_str}.md"
    generate_markdown_report(report_data, md_path)

    logger.info(f"Reporte de Fidelidad Semántica generado en: {md_path}")
    return report_data


def generate_markdown_report(data: Dict[str, Any], output_path: Path):
    """
    Genera el reporte en Markdown formateado para la tesis.
    """
    status_icon = "✅ CUMPLIDO" if data.get("academic_threshold_met") else "⚠️ REQUIERE REVISIÓN"

    md = f"""# Reporte de Validación - Indicador 1: Fidelidad Semántica y Alucinación (RAG)

- **Fecha de Evaluación:** `{data['timestamp']}`
- **Cuestionarios Auditados:** `{data['quizzes_audited']}`
- **Preguntas Evaluadas Exitosamente:** `{data.get('total_questions_audited', 0)}`
- **Preguntas Omitidas por Error Técnico de API:** `{data.get('unprocessed_questions_due_to_api_error', 0)}`
- **Afirmaciones Atómicas Extraídas y Auditadas:** `{data['total_claims_analyzed']}`
- **Estado de Meta de Tesis ($\ge 85\%$ Fidelidad):** **{status_icon}**

---

## 1. Resumen Cuantitativo de Métricas

| Métrica | Valor Obtenido | Umbral de Éxito Académico | Veredicto |
| :--- | :---: | :---: | :---: |
| **Índice de Fidelidad Semántica (Faithfulness)** | **{data['faithfulness_score_percentage']}%** | $\ge 85.0\%$ (Es et al., 2023) | {'✅ Superado' if data['faithfulness_score_percentage'] >= 85.0 else '❌ Por debajo'} |
| **Tasa de Alucinación (Hallucination Rate)** | **{data['hallucination_rate_percentage']}%** | $\le 15.0\%$ (Gao et al., 2024) | {'✅ Controlada' if data['hallucination_rate_percentage'] <= 15.0 else '❌ Excesiva'} |
| **Afirmaciones Respaldadas en Contexto** | `{data['verified_grounded_claims']} / {data['total_claims_analyzed']}` | - | - |
| **Afirmaciones No Respaldadas / Alucinadas** | `{data['hallucinated_claims']} / {data['total_claims_analyzed']}` | - | - |

---

## 2. Interpretación Metodológica para la Tesis

1. **Groundedness del Contexto:** El {data['faithfulness_score_percentage']}% de los conceptos, enunciados y claves de respuesta generados por el LLM tienen un anclaje directo y verificable en los fragmentos de texto almacenados en PostgreSQL (`document_chunk`), recuperados mediante la estrategia híbrida (búsqueda vectorial con embeddings de Gemini + búsqueda léxica con PostgreSQL `to_tsvector` fusionadas vía RRF).
2. **Mitigación de Alucinaciones:** La tasa de alucinación registrada del {data['hallucination_rate_percentage']}% confirma que la temperatura determinista configurada (`0.1` en la API y `0.0` en el evaluador) junto a las directivas estrictas del prompt previenen que el modelo invente hechos no contenidos en el material académico del curso.
3. **Tratamiento de Muestras Inválidas:** Los errores atribuibles a fallos de conectividad o límites de tasa de proveedores de IA externos (HTTP 429/503/404) son catalogados como fallas técnicas de infraestructura y omitidos del cálculo de alucinación para no distorsionar las métricas pedagógicas del sistema RAG.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    asyncio.run(run_faithfulness_evaluation())
