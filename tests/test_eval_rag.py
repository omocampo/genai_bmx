import os
import pytest
from google import genai
from pydantic import BaseModel, Field
from src.config import settings


class FaithfulnessScore(BaseModel):
    is_faithful: bool = Field(description="True si la respuesta no inventa datos fuera del contexto.")
    score: float = Field(description="Puntaje de 0.0 a 1.0 de fidelidad al contexto.")
    reasoning: str = Field(description="Breve justificación de la calificación.")


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="Requiere GEMINI_API_KEY")
def test_rag_faithfulness_judge():
    """Evalúa mediante LLM-as-a-Judge que el asistente no alucine tasas financieras."""
    client = genai.Client(api_key=settings.gemini_api_key)

    context = (
        "Tarjeta de Crédito Joy Banamex: Ingreso mínimo $7,000 MXN. "
        "Anualidad $0 MXN realizando al menos 1 compra al mes de $1 peso. CAT Promedio: 82.4% sin IVA."
    )
    generated_answer = (
        "La Tarjeta Joy Banamex no cobra anualidad si realizas al menos una compra de $1 al mes. "
        "Requiere un ingreso mínimo de $7,000 MXN y tiene un CAT promedio informativo de 82.4% sin IVA."
    )

    prompt = f"""Evalúa si la RESPUESTA GENERADA se basa estrictamente en el CONTEXTO OFICIAL sin inventar cifras.
CONTEXTO OFICIAL: {context}
RESPUESTA GENERADA: {generated_answer}"""

    response = client.models.generate_content(
        model=settings.gemini_model.strip(),
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": FaithfulnessScore,
        },
    )
    result = FaithfulnessScore.model_validate_json(response.text)
    assert result.is_faithful is True
    assert result.score >= 0.9

