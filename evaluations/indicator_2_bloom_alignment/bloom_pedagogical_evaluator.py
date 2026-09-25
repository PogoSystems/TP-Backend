"""
Juez pedagógico independiente para clasificación ciega de Taxonomía de Bloom.
Evalúa preguntas generadas sin conocer previamente la etiqueta original asignada,
evitando sesgos y emitiendo un juicio riguroso según la taxonomía cognitiva revisada de Bloom.
Incluye contingencia transparente a Groq ante cuotas agotadas (429) de Gemini.
"""

import json
import logging
from typing import Dict, List, Optional
from google import genai
from google.genai import types
from groq import AsyncGroq
from pydantic import BaseModel, Field
import asyncio

from core.settings import settings

logger = logging.getLogger(__name__)

BLOOM_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate"]


class BloomClassificationResult(BaseModel):
    cognitive_level: str = Field(
        description="Nivel cognitivo predominante requerido para resolver el reactivo. Debe ser exactamente uno de: 'remember', 'understand', 'apply', 'analyze', 'evaluate'."
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Nivel de certeza de la clasificación (0.0 a 1.0)"
    )
    cognitive_demand_analysis: str = Field(
        description="Breve justificación pedagógica analizando los procesos mentales que el estudiante debe movilizar"
    )
    action_verbs_identified: List[str] = Field(
        default_factory=list, description="Verbos u operaciones cognitivas identificadas"
    )


class BloomPedagogicalEvaluator:
    """
    Evaluador experto en educación que clasifica reactivos según la Taxonomía de Bloom
    con contingencia automática a Groq.
    """

    def __init__(self):
        self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._gemini_model = settings.GEMINI_MODEL
        self._groq_client: Optional[AsyncGroq] = None
        self._groq_model: str = "openai/gpt-oss-20b"
        if settings.GROQ_API_KEY:
            self._groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def evaluate_question_bloom_level(
        self,
        question_text: str,
        answers: List[str],
        explanation: str,
    ) -> Optional[BloomClassificationResult]:
        """
        Clasifica una pregunta en forma ciega (sin recibir la etiqueta original).
        """
        options_text = "\n".join([f"- {opt}" for opt in answers])

        prompt = f"""
Eres un psicólogo educativo y experto en diseño curricular especializado en la Taxonomía Cognitiva de Bloom (Revisada por Anderson & Krathwohl).
Tu tarea es analizar el siguiente reactivo de evaluación de forma estrictamente ciega y determinar qué nivel de complejidad cognitiva demanda del estudiante para ser respondido correctamente.

Reactivo:
Enunciado: {question_text}
Opciones de respuesta:
{options_text}
Explicación didáctica: {explanation}

Criterios de Clasificación según la Taxonomía de Bloom:
1. 'remember': Recuperar, reconocer, listar o recordar datos, fechas, definiciones literales o hechos sin necesidad de interpretar su significado profundo.
2. 'understand': Demostrar comprensión traduciendo, resumiendo, interpretando, parafraseando o explicando conceptos e ideas con palabras propias.
3. 'apply': Transferir y usar un concepto, procedimiento, fórmula, técnica o regla para resolver un problema práctico o situación inédita.
4. 'analyze': Descomponer información en sus componentes esenciales, distinguir causas y efectos, identificar falacias, comparar elementos estructurales o determinar relaciones implícitas.
5. 'evaluate': Emitir o justificar juicios de valor, críticas o decisiones fundamentadas usando criterios y estándares explícitos.

Instrucciones:
- No clasifiques por la presencia superficial de un verbo; analiza el proceso mental real que el estudiante debe ejecutar.
- Asigna exactamente uno de los 5 niveles: 'remember', 'understand', 'apply', 'analyze', 'evaluate'.
- Genera la respuesta respetando el esquema JSON solicitado.
"""

        try:
            response = await self._gemini_client.aio.models.generate_content(
                model=self._gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BloomClassificationResult,
                    temperature=0.0,
                ),
            )

            if not response.text:
                raise ValueError("Respuesta vacía del clasificador de Bloom")

            result = BloomClassificationResult.model_validate_json(response.text)
            return self._normalize_result(result)

        except Exception as e:
            # Si Gemini falla por cualquier razón (404, 429, 503, etc.), pasar a Groq
            if self._groq_client:
                logger.warning(f"Gemini API no disponible para clasificación de Bloom ({e}). Activando fallback a Groq ({self._groq_model})...")
                return await self._evaluate_with_groq(prompt)

            logger.error(f"Fallo clasificando pregunta de Bloom sin evaluador secundario disponible: {e}")
            return None

    async def _evaluate_with_groq(self, prompt: str, max_retries: int = 4) -> Optional[BloomClassificationResult]:
        """
        Fallback a Groq con reintentos y backoff exponencial ante límites de tasa (429) o fallos de servidor.
        """
        schema_json = BloomClassificationResult.model_json_schema()
        system_instruction = (
            "Eres un psicólogo educativo experto en la Taxonomía de Bloom. "
            "Debes retornar obligatoriamente un JSON válido cumpliendo este JSON Schema exacto:\n"
            f"{json.dumps(schema_json, ensure_ascii=False)}\n"
            "No agregues texto conversacional fuera del JSON."
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

                result = BloomClassificationResult.model_validate_json(clean_json)
                return self._normalize_result(result)
            except Exception as groq_err:
                err_str = str(groq_err)
                is_rate_limit = "429" in err_str or "rate_limit" in err_str.lower() or "too many requests" in err_str.lower()
                is_server_error = "500" in err_str or "503" in err_str

                if (is_rate_limit or is_server_error) and attempt < max_retries:
                    wait_time = 2.5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"Groq API {('Rate limit (429)' if is_rate_limit else 'Error de servidor')} en clasificador de Bloom (intento {attempt}/{max_retries}). "
                        f"Esperando {wait_time:.1f}s antes de reintentar..."
                    )
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f"Fallo definitivo en evaluador Groq para Bloom: {groq_err}")
                return None

    @staticmethod
    def _normalize_result(result: BloomClassificationResult) -> BloomClassificationResult:
        clean_level = result.cognitive_level.strip().lower()
        if clean_level not in BLOOM_LEVELS:
            for valid in BLOOM_LEVELS:
                if valid in clean_level:
                    clean_level = valid
                    break
            else:
                clean_level = "remember"
        result.cognitive_level = clean_level
        return result
