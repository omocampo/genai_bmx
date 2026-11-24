from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Petición enviada desde el frontend hacia el orquestador."""

    session_id: str = Field(
        ...,
        description="Identificador único de la sesión de conversación.",
        examples=["demo-session-001"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Mensaje del usuario.",
        examples=["Quiero simular una hipoteca de 2.5 millones a 15 años"],
    )
    customer_id: Optional[str] = Field(
        default=None,
        description="ID opcional del cliente simulado (ej. CUST-1001).",
    )


class ChatResponse(BaseModel):
    """Respuesta estructurada con metadatos de observabilidad."""

    session_id: str
    reply: str
    active_agent: str
    tools_executed: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_docs: list[str] = Field(default_factory=list)

