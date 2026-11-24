from typing import Optional
from langchain_core.messages import AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.agents.state import AgentState
from src.config import settings
from src.database.vector_store import get_vector_store


class CustomerCardProfile(BaseModel):
    """Esquema estructurado para extraer el perfil financiero del usuario."""

    monthly_income: Optional[float] = Field(
        default=None,
        description="Ingreso mensual estimado del usuario en pesos mexicanos (MXN), si lo mencionó.",
    )
    main_spending_category: Optional[str] = Field(
        default=None,
        description="Categoría principal de gasto o interés (ej. 'conciertos', 'sin anualidad', 'costco', 'puntos/viajes').",
    )
    has_enough_info: bool = Field(
        default=False,
        description="True si el usuario ya dio suficiente contexto o hace una pregunta directa sobre una tarjeta específica.",
    )


CARDS_SYSTEM_PROMPT = """Eres el Especialista en Tarjetas de Crédito de Banamex.
Tu objetivo es ayudar al cliente a elegir la mejor tarjeta del catálogo o resolver dudas sobre comisiones, CAT, anualidad y beneficios.

REGLAS ESTRICTAS:
1. Basa tus respuestas ÚNICAMENTE en el contexto oficial recuperado de la base de conocimiento. No inventes tasas, comisiones ni requisitos.
2. Si el usuario pide una recomendación pero aún no menciona su ingreso mensual aproximado ni en qué suele gastar más, hazle 1 o 2 preguntas breves y 
amables para perfilarlo antes de recomendar.
3. Si ya tienes contexto suficiente (o pregunta por una tarjeta específica como Joy, Oro, LineUp o Costco), presenta la mejor opción (o compara hasta 2 
opciones) destacando:
   - Por qué encaja con su perfil.
   - Ingreso mínimo requerido y anualidad.
   - CAT promedio informativo (obligatorio por transparencia bancaria).
4. Mantén un tono profesional, cercano y claro. Usa formato Markdown limpio con viñetas.

CONTEXTO OFICIAL RECUPERADO (RAG):
{context}
"""


def cards_agent_node(state: AgentState) -> dict:
    """Nodo de LangGraph para el especialista de Tarjetas de Crédito."""
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.2,
    )

    messages = state["messages"]
    last_user_msg = messages[-1].content

    # 1. Perfilamiento estructurado (Structured Output)
    profiler_llm = llm.with_structured_output(CustomerCardProfile)
    profile: CustomerCardProfile = profiler_llm.invoke(
        [
            SystemMessage(
                content="Extrae el perfil financiero del usuario a partir del historial de conversación."
            ),
            *messages[-4:],  # Últimos turnos para contexto reciente
        ]
    )

    # 2. Búsqueda Semántica (RAG en pgvector)
    # Enriquecemos la query con la categoría detectada para mejorar la precisión del retrieval
    search_query = f"{last_user_msg} {profile.main_spending_category or ''}".strip()
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(search_query, k=3)

    context_text = "\n\n---\n\n".join(doc.page_content for doc in docs)
    retrieved_sources = [
        f"{doc.metadata.get('producto', 'Catálogo')} (Chunk #{doc.metadata.get('chunk_id', '?')})"
        for doc in docs
    ]

    # 3. Generación de respuesta fundamentada
    system_prompt = CARDS_SYSTEM_PROMPT.format(context=context_text)
    response = llm.invoke([SystemMessage(content=system_prompt), *messages])

    # Registro de observabilidad para mostrar en la interfaz
    tool_log = {
        "agent": "CardsAgent",
        "action": "RAG_Similarity_Search + Structured_Profiling",
        "extracted_profile": profile.model_dump(),
        "sources_used": retrieved_sources,
    }

    return {
        "messages": [AIMessage(content=response.content)],
        "active_agent": "CardsAgent (Tarjetas & RAG)",
        "retrieved_docs": retrieved_sources,
        "tools_executed": state.get("tools_executed", []) + [tool_log],
    }

