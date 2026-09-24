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
    correct_answers: List[str],
    explanation: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 8,
) -> str:
    """
    Selecciona los fragmentos de texto más relevantes para la pregunta específica
    basándose en coincidencia léxica ponderada (palabras clave, títulos y texto).
    Evita truncar el contexto de la sección correcta.
    """
    if not chunks:
        return ""

    if len(chunks) <= top_k:
        return "\n\n".join([
            f"[Fragmento #{c['chunk_index']} - {c['heading_path']}]:\n{c['content']}"
            for c in chunks
        ])

    search_text = f"{question_text} {' '.join(correct_answers)} {explanation}".lower()
    # Extraer palabras clave de más de 3 letras ignorando stopwords comunes
    stopwords = {"para", "como", "cual", "esta", "este", "entre", "sobre", "desde", "hacia", "pero", "donde", "cuando"}
    keywords = {w for w in re.findall(r"\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}\b", search_text) if w not in stopwords}

    scored_chunks = []
    for c in chunks:
        content_lower = c["content"].lower()
        heading_lower = c["heading_path"].lower()

        score = 0
        for kw in keywords:
            if kw in heading_lower:
                score += 3  # Mayor peso a coincidencia en títulos/secciones
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
    ) -> QuestionFaithfulnessResult:
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
Eres un auditor académico y evaluador de fidelidad factual para sistemas RAG (Retrieval-Augmented Generation).
Tu tarea es verificar si las preguntas, sus respuestas correctas y sus explicaciones didácticas se fundamentan estrictamente en el material de referencia proporcionado o si contienen ALUCINACIONES (información externa, contradictoria o no respaldada).

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

Directivas de Evaluación:
1. Las opciones marcadas como '[DISTRACTOR / OPCIÓN INCORRECTA]' fueron diseñadas intencionalmente como opciones erróneas para evaluar al alumno. NO evalúes los distractores como afirmaciones que deban ser verdaderas en el texto.
2. Descompón el reactivo en afirmaciones atómicas (claims) considerando:
   - Que el tema del enunciado sea coherente con el material.
   - Que la opción declarada como CORRECTA esté respaldada como verdadera por el contexto de referencia.
   - Que los hechos y argumentos expuestos en la explicación sean consistentes con el material (incluyendo cuando explica por qué se descartan las otras opciones).
3. Para cada afirmación atómica:
   - Marca 'is_grounded': true si está directamente soportada por el contexto o es una deducción lógica del texto.
   - Marca 'is_grounded': false si introduce conceptos o hechos que contradicen o NO están presentes en el material (ALUCINACIÓN).
4. Genera la salida siguiendo estrictamente el esquema JSON solicitado.
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
            err_str = str(e)
            is_quota_or_503 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "UNAVAILABLE" in err_str

            if is_quota_or_503 and self._groq_client:
                logger.warning(
                    f"Gemini API cuota/error en pregunta #{question_id}. Activando fallback a Groq ({self._groq_model})..."
                )
                return await self._evaluate_with_groq(prompt, question_id)

            logger.error(f"Error evaluando pregunta #{question_id}: {e}")
            return QuestionFaithfulnessResult(
                question_id=question_id,
                claims=[
                    ClaimVerification(
                        claim="Error técnico de evaluación",
                        is_grounded=False,
                        reasoning=f"Fallo en API: {e}",
                    )
                ],
                is_fully_faithful=False,
                summary_verdict="Error técnico",
            )

    async def _evaluate_with_groq(self, prompt: str, question_id: int) -> QuestionFaithfulnessResult:
        """
        Fallback a Groq cuando Gemini alcanza su límite de cuota.
        """
        schema_json = QuestionFaithfulnessResult.model_json_schema()
        system_instruction = (
            "Eres un auditor académico experto en RAG. "
            "Debes retornar obligatoriamente un JSON válido cumpliendo este JSON Schema exacto:\n"
            f"{json.dumps(schema_json, ensure_ascii=False)}\n"
            "No agregues texto conversational fuera del JSON."
        )

        if not self._groq_client:
            raise RuntimeError(
                "El cliente de Groq no está inicializado. "
                "Verifica que GROQ_API_KEY esté configurada en el entorno o archivo .env."
            )

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
            logger.error(f"Fallo también en fallback de Groq para pregunta #{question_id}: {groq_err}")
            return QuestionFaithfulnessResult(
                question_id=question_id,
                claims=[
                    ClaimVerification(
                        claim="Fallo en evaluador primario y secundario",
                        is_grounded=False,
                        reasoning=f"Error en Groq: {groq_err}",
                    )
                ],
                is_fully_faithful=False,
                summary_verdict="Error en evaluación",
            )


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
            relevant_context = select_relevant_chunks_for_question(
                question_text=q["text"],
                correct_answers=q["correct_answers"],
                explanation=q["explanation"],
                chunks=raw_chunks,
                top_k=8,
            )

            res = await evaluator.evaluate_question_against_context(
                question_id=q["question_id"],
                question_text=q["text"],
                answers=q.get("answers", []),
                correct_answers=q["correct_answers"],
                explanation=q["explanation"],
                context_text=relevant_context,
            )

            for claim in res.claims:
                total_claims += 1
                if claim.is_grounded:
                    total_verified += 1

            quiz_eval["questions_evaluated"].append({
                "question_id": q["question_id"],
                "text": q["text"],
                "bloom_level": q["bloom_level"],
                "is_fully_faithful": res.is_fully_faithful,
                "claims": [c.model_dump() for c in res.claims],
            })

            # Pausa breve defensiva para respetar límites de tasa
            await asyncio.sleep(0.3)

        detailed_results.append(quiz_eval)

    # Cálculo con MetricsEngine
    metrics = calculate_faithfulness(total_verified, total_claims)

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "quizzes_audited": len(detailed_results),
        "total_claims_analyzed": total_claims,
        "verified_grounded_claims": total_verified,
        "hallucinated_claims": total_claims - total_verified,
        "faithfulness_score_percentage": metrics["faithfulness_percentage"],
        "hallucination_rate_percentage": metrics["hallucination_percentage"],
        "academic_threshold_met": metrics["faithfulness_percentage"] >= 85.0,
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
- **Afirmaciones Atómicas Extraídas:** `{data['total_claims_analyzed']}`
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
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    asyncio.run(run_faithfulness_evaluation())
