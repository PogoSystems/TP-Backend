import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError

from core.settings import settings
from modules.quiz_generation.domain.ports.quiz_generator_port import QuizGeneratorPort
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz
from shared.value_objects.Bloom import BloomLevel

logger = logging.getLogger(__name__)


class GeminiQuizGenerator():
    """
    Gemini implementation of the QuizGeneratorPort.
    Responsible for sending prompt and context to Gemini using Structured Output.
    """

    def __init__(self, *, client: genai.Client) -> None:
        self._client = client
        self._model = settings.GEMINI_MODEL

    async def generate_quiz_from_context(
        self,
        *,
        context_text: str,
        num_questions: int,
        bloom_levels: list[BloomLevel]
    ) -> GeneratedQuiz:
        """
        Generate structured quiz using Gemini API.
        """
        bloom_instruction = ""
        focused_bloom_levels = ""
        if bloom_levels:
            for bloom_level in bloom_levels:
                match bloom_level:
                    case BloomLevel.REMEMBER:
                        focused_bloom_levels += (
                            "- Remember: Test pure retrieval and recognition of explicit definitions, facts, acronyms, or specific terminology directly stated in the context.\n"
                        )
                    case BloomLevel.UNDERSTAND:
                        focused_bloom_levels += (
                            "- Understand: The student must demonstrate conceptual comprehension by explaining cause-and-effect mechanisms, conceptual consequences, or interpreting relationships in their own words.\n"
                            "  * POSITIVE PATTERNS:\n"
                            "    - Present a conceptual cause-effect scenario: e.g. What is the fundamental theoretical consequence on project control and verification if bidirectional traceability is omitted during a requirements change?\n"
                            "    - Contrast the underlying purpose of two related engineering concepts (e.g. explaining the distinction between verification 'building the product right' vs validation 'building the right product' in practice).\n"
                            "    - Paraphrase and explain why a specific engineering principle or mechanism is necessary conceptually.\n"
                            "  * STRICT BOUNDARIES (WHAT NOT TO DO):\n"
                            "    - Do NOT ask '¿Cuál es la intención/propósito de [X]?' or '¿Cuál es la definición de [X]?'.\n"
                            "    - Do NOT ask questions that can be answered by recalling a verbatim sentence under headers like 'Intención', 'Valor' or 'Definición'. That is 'Remember'.\n"
                        )
                    case BloomLevel.APPLY:
                        focused_bloom_levels += (
                            "- Apply: The student must APPLY a rule, standard procedure, or protocol to determine the correct operational course of action in a concrete project scenario or incident.\n"
                            "  * POSITIVE PATTERNS:\n"
                            "    - Present a concrete, realistic project dilemma or operational incident (e.g. 'A client submits an emergency change to an already approved baseline LB-01 during a release cycle; according to Configuration Management procedures, what is the immediate procedural step the engineering team must take?').\n"
                            "    - Classify an unencountered incident or scenario into the correct procedural category according to established criteria.\n"
                            "    - Determine the appropriate sequence of procedural actions to handle a defect, change request, or process violation in a project scenario.\n"
                            "  * STRICT BOUNDARIES (WHAT NOT TO DO):\n"
                            "    - PURELY THEORETICAL / CONCEPTUAL: Do NOT include mathematical calculations, arithmetic, formulas, or numerical computations.\n"
                            "    - Do NOT ask for the code, name, inputs, or outputs of a standard practice (e.g. do NOT ask 'What documents are inputs to RDM 3.3?' or 'Which practice code prescribes X?' - that is 'Remember').\n"
                            "    - Do NOT ask which step contains a subtle architectural flaw or diagnose root causes (that is 'Analyze').\n"
                            "    - Do NOT ask to critique or justify whether a framework/tool was the right choice (that is 'Evaluate').\n"
                        )
                    case BloomLevel.ANALYZE:
                        focused_bloom_levels += (
                            "- Analyze: The student must DECONSTRUCT a given technical scenario to diagnose the root cause of an issue, identify a structural defect, or examine implicit relationships between components.\n"
                            "  * POSITIVE PATTERNS:\n"
                            "    - Present a concrete multi-step scenario and ask to diagnose which specific step introduces fragility or violates an architectural principle.\n"
                            "    - Present two contrasting test cases or designs and ask to identify the underlying structural reason why one succeeds where the other fails.\n"
                            "  * STRICT BOUNDARIES (WHAT NOT TO DO):\n"
                            "    - Do NOT ask for bullet points, lists of differences, or trade-offs that are explicitly stated word-for-word in the text (e.g. do not ask 'what is the audience difference between TDD and BDD'). The student must analyze an unencountered scenario.\n"
                        )
                    case BloomLevel.EVALUATE:
                        focused_bloom_levels += (
                            "- Evaluate: The student must JUDGE, CRITIQUE, or JUSTIFY a decision between competing, viable alternatives by weighing trade-offs and criteria (e.g. assessing whether a team should adopt BDD despite its maintenance overhead under specific project constraints, or critiquing an architectural proposal against quality standards).\n"
                            "  * POSITIVE PATTERNS:\n"
                            "    - Present a situation where two valid engineering strategies conflict (e.g. high upfront maintenance vs fast feedback) and ask the student to justify which one is superior given specific business constraints.\n"
                            "    - Ask to critique an engineering proposal by assessing whether its stated benefits justify its documented trade-offs.\n"
                        )
            bloom_instruction = (
                f"\nCRITICAL INSTRUCTION: Focus EXCLUSIVELY on these levels of Bloom's Taxonomy and their operational definitions:\n"
                f"{focused_bloom_levels}\n"
                "Ensure that each question's actual mental task truly aligns with its assigned Bloom level, avoiding superficial phrasing.\n"
            )
        prompt = f"""
You are an expert educator. Generate exactly {num_questions} quiz questions in Spanish.

Bloom level:
{bloom_instruction}

The reference material contains:
1. Syllabus objectives and competencies.
2. Course content retrieved through RAG.

Every question must:
- Align with at least one syllabus objective or competency.
- Be answerable from the provided course content.
- Match the specified Bloom cognitive level, if specified.
- Test the student's knowledge rather than the ability to recall the wording of the source.
- Avoid mentioning the reference material, documents, or text.
- Use only information supported by the provided material.
- STRICT FIDELITY RULE: Use ONLY factual information explicitly contained in the reference material. If a concept, author, standard, acronym, or methodology is ONLY named as a bullet point, list item, or title WITHOUT an explicit conceptual explanation or definition in the reference material, DO NOT invent or expand its details, components, or definitions using external knowledge. Generate questions exclusively about topics whose core concepts and explanations are present in the provided text.

Question types: Multiple Choice or True/False.

For Multiple Choice questions, provide one unambiguously correct answer and plausible distractors based on common misunderstandings.
Avoid making the correct choice considerably longer or shorter than the distractors, try to make them similar in length and complexity.
For True/False questions, ensure the statement is clearly true or false according to the course content.

Reference material:
---
{context_text}
---

Generate the output strictly following the requested JSON schema.
"""

        try:
            # Call Gemini using async client
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeneratedQuiz,
                    temperature=0.1,  # Low temperature for factual consistency
                ),
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response")

            logger.info("Successfully received response from Gemini API for quiz generation")
            # Parse and run Pydantic validators on our side to guarantee correctness
            return GeneratedQuiz.model_validate_json(response.text)

        except APIError as e:
            is_503 = getattr(e, "code", None) == 503 or "503" in str(e) or "UNAVAILABLE" in str(e).upper() or "HIGH DEMAND" in str(e).upper()
            if is_503 and settings.GROQ_API_KEY:
                logger.warning(
                    f"Gemini API returned 503 UNAVAILABLE. Initiating fallback to Groq ({settings.GROQ_MODEL})..."
                )
                return await self._generate_with_groq(prompt)

            logger.error(f"Gemini APIError during quiz generation: {e}")
            raise RuntimeError(f"Gemini API error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during quiz generation: {e}")
            raise RuntimeError(f"Quiz generation failed: {e}") from e

    async def _generate_with_groq(self, prompt: str) -> GeneratedQuiz:
        """
        Fallback generator using Groq when Gemini is unavailable.
        """
        from groq import AsyncGroq

        groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        schema_json = GeneratedQuiz.model_json_schema()
        try:
            completion = await groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert educator. Return valid JSON adhering strictly to this JSON Schema:\n"
                            f"{schema_json}\n"
                            "Do not include any conversational commentary or markdown code fence blocks."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            content = completion.choices[0].message.content
            if not content:
                raise ValueError("Groq returned an empty response")

            clean_json = content.strip()
            if clean_json.startswith("```"):
                clean_json = clean_json.split("\n", 1)[1]
            if clean_json.endswith("```"):
                clean_json = clean_json.rsplit("```", 1)[0]
            clean_json = clean_json.strip()

            logger.info("Successfully generated quiz via Groq fallback")
            return GeneratedQuiz.model_validate_json(clean_json)
        except Exception as err:
            logger.error(f"Groq fallback failed during quiz generation: {err}")
            raise RuntimeError(f"Fallback to Groq failed after Gemini 503: {err}") from err

