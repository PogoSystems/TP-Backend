import pytest
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz, GeneratedQuestion, GeneratedAnswer
from modules.llm_adapter.infrastructure.providers.gemini_quiz_generator import shuffle_quiz_options
from shared.value_objects.Bloom import BloomLevel


def make_quiz_with_multiple_questions() -> GeneratedQuiz:
    return GeneratedQuiz(
        title="Test Shuffle Quiz",
        questions=[
            GeneratedQuestion(
                text="Pregunta 1: Arquitectura Limpia",
                bloom_level=BloomLevel.UNDERSTAND,
                score=10,
                explanation="Explicación P1",
                answers=[
                    GeneratedAnswer(text="Opción Q1 Correcta", is_correct=True),
                    GeneratedAnswer(text="Opción Q1 Distractor 1", is_correct=False),
                    GeneratedAnswer(text="Opción Q1 Distractor 2", is_correct=False),
                    GeneratedAnswer(text="Opción Q1 Distractor 3", is_correct=False),
                ],
            ),
            GeneratedQuestion(
                text="Pregunta 2: Domain-Driven Design",
                bloom_level=BloomLevel.APPLY,
                score=10,
                explanation="Explicación P2",
                answers=[
                    GeneratedAnswer(text="Opción Q2 Correcta", is_correct=True),
                    GeneratedAnswer(text="Opción Q2 Distractor 1", is_correct=False),
                    GeneratedAnswer(text="Opción Q2 Distractor 2", is_correct=False),
                    GeneratedAnswer(text="Opción Q2 Distractor 3", is_correct=False),
                ],
            ),
            GeneratedQuestion(
                text="Pregunta 3: Patrón Repository",
                bloom_level=BloomLevel.ANALYZE,
                score=10,
                explanation="Explicación P3",
                answers=[
                    GeneratedAnswer(text="Opción Q3 Correcta", is_correct=True),
                    GeneratedAnswer(text="Opción Q3 Distractor 1", is_correct=False),
                    GeneratedAnswer(text="Opción Q3 Distractor 2", is_correct=False),
                    GeneratedAnswer(text="Opción Q3 Distractor 3", is_correct=False),
                ],
            ),
        ],
    )


def test_shuffle_isolates_questions_and_prevents_leakage():
    """
    Verifica que las opciones se barajan estrictamente DENTRO de cada pregunta.
    Ninguna opción de la pregunta 1 debe terminar en la pregunta 2 o 3.
    """
    quiz = make_quiz_with_multiple_questions()
    shuffled = shuffle_quiz_options(quiz)

    # Conjuntos de textos originales por pregunta
    q1_texts = {"Opción Q1 Correcta", "Opción Q1 Distractor 1", "Opción Q1 Distractor 2", "Opción Q1 Distractor 3"}
    q2_texts = {"Opción Q2 Correcta", "Opción Q2 Distractor 1", "Opción Q2 Distractor 2", "Opción Q2 Distractor 3"}
    q3_texts = {"Opción Q3 Correcta", "Opción Q3 Distractor 1", "Opción Q3 Distractor 2", "Opción Q3 Distractor 3"}

    # Comprobación de no-fuga y pertenencia estricta
    assert {a.text for a in shuffled.questions[0].answers} == q1_texts
    assert {a.text for a in shuffled.questions[1].answers} == q2_texts
    assert {a.text for a in shuffled.questions[2].answers} == q3_texts


def test_shuffle_preserves_correct_answer_pairing():
    """
    Verifica que el atributo is_correct viaje siempre acoplado a su texto correspondiente
    y que siga habiendo exactamente una respuesta correcta por pregunta.
    """
    quiz = make_quiz_with_multiple_questions()
    shuffled = shuffle_quiz_options(quiz)

    for question in shuffled.questions:
        correct_answers = [a for a in question.answers if a.is_correct]
        assert len(correct_answers) == 1, "Debe existir exactamente 1 respuesta correcta"
        assert "Correcta" in correct_answers[0].text, "El texto de la respuesta correcta debe permanecer con is_correct=True"

        incorrect_answers = [a for a in question.answers if not a.is_correct]
        assert len(incorrect_answers) == 3
        for inc in incorrect_answers:
            assert "Distractor" in inc.text, "Los distractores deben permanecer con is_correct=False"


def test_shuffle_mitigates_positional_bias_statistically():
    """
    Verifica que el índice de la opción correcta ya no sea siempre 0,
    sino que se distribuya entre las distintas posiciones (0, 1, 2, 3) en múltiples ejecuciones.
    """
    observed_indices = set()
    num_trials = 50

    for _ in range(num_trials):
        quiz = make_quiz_with_multiple_questions()
        shuffled = shuffle_quiz_options(quiz)
        for q in shuffled.questions:
            idx = next(i for i, a in enumerate(q.answers) if a.is_correct)
            observed_indices.add(idx)

    # Con 50 pruebas y 3 preguntas por prueba (150 muestras), la respuesta correcta
    # debe haber caído en múltiples índices distintos de 0.
    assert len(observed_indices) > 1, f"La respuesta correcta debería aparecer en múltiples posiciones. Observadas: {observed_indices}"
    assert observed_indices.issubset({0, 1, 2, 3})


def test_true_false_conventional_ordering_preserved():
    """
    Verifica que las preguntas de 2 opciones tipo Verdadero/Falso respeten el orden
    convencional ('Verdadero' primero, 'Falso' segundo), incluso si el LLM las generó invertidas.
    """
    quiz = GeneratedQuiz(
        title="True False Quiz",
        questions=[
            # Caso 1: Vino invertido ('Falso' primero, 'Verdadero' segundo con Verdadero correcto)
            GeneratedQuestion(
                text="¿Python es un lenguaje interpretado?",
                bloom_level=BloomLevel.REMEMBER,
                score=5,
                explanation="Python es interpretado y compilado a bytecode.",
                answers=[
                    GeneratedAnswer(text="Falso", is_correct=False),
                    GeneratedAnswer(text="Verdadero", is_correct=True),
                ],
            ),
            # Caso 2: Vino convencional pero con Falso correcto
            GeneratedQuestion(
                text="¿SQLAlchemy es un motor NoSQL?",
                bloom_level=BloomLevel.REMEMBER,
                score=5,
                explanation="SQLAlchemy es un ORM relacional SQL.",
                answers=[
                    GeneratedAnswer(text="Verdadero", is_correct=False),
                    GeneratedAnswer(text="Falso", is_correct=True),
                ],
            ),
        ],
    )

    shuffled = shuffle_quiz_options(quiz)

    # Pregunta 1
    q1 = shuffled.questions[0]
    assert len(q1.answers) == 2
    assert q1.answers[0].text == "Verdadero" and q1.answers[0].is_correct is True
    assert q1.answers[1].text == "Falso" and q1.answers[1].is_correct is False

    # Pregunta 2
    q2 = shuffled.questions[1]
    assert len(q2.answers) == 2
    assert q2.answers[0].text == "Verdadero" and q2.answers[0].is_correct is False
    assert q2.answers[1].text == "Falso" and q2.answers[1].is_correct is True


def test_pydantic_schema_integrity_after_shuffle():
    """
    Verifica que la serialización a dict y JSON siga funcionando y cumpla estrictamente
    con el esquema Pydantic GeneratedQuiz sin romper ningún tipo.
    """
    quiz = make_quiz_with_multiple_questions()
    shuffled = shuffle_quiz_options(quiz)

    quiz_dict = shuffled.model_dump()
    assert "title" in quiz_dict
    assert "questions" in quiz_dict
    assert len(quiz_dict["questions"]) == 3

    # Revalidación a partir del dump
    revalidated = GeneratedQuiz.model_validate(quiz_dict)
    assert isinstance(revalidated, GeneratedQuiz)
    assert revalidated.title == quiz.title
