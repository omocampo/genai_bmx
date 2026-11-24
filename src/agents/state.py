from typing import Annotated, Any, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Estado compartido que fluye entre el Supervisor y los Agentes Especialistas."""

    # Historial de conversación (add_messages concatena automáticamente nuevos turnos)
    messages: Annotated[list[BaseMessage], add_messages]

    # Contexto opcional del cliente autenticado (ej. 'CUST-1001')
    customer_id: str | None

    # Metadatos de observabilidad para el panel de control de la entrevista
    active_agent: str
    tools_executed: list[dict[str, Any]]
    retrieved_docs: list[str]

