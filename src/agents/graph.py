from typing import Literal
from langchain_core.messages import AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.agents.cards_agent import cards_agent_node
from src.agents.guardrails import check_input_guardrails, check_output_guardrails
from src.agents.mortgage_agent import mortgage_agent_node
from src.agents.security_agent import security_agent_node
from src.agents.state import AgentState
from src.config import settings


class RouteDecision(BaseModel):
    """Decisión de enrutamiento del agente supervisor."""

    next_agent: Literal[
        "cards_agent", "mortgage_agent", "security_agent", "general_greeting"
    ] = Field(
        description=(
            "El agente especialista que debe atender la solicitud: "
            "'cards_agent' para tarjetas de crédito, anualidades, CAT o recomendaciones; "
            "'mortgage_agent' para créditos hipotecarios, simulación de mensualidades o compra de vivienda; "
            "'security_agent' para cargos no reconocidos, fraudes, movimientos sospechosos o bloqueo de tarjeta; "
            "'general_greeting' únicamente para saludos simples o preguntas fuera del ámbito bancario."
        )
    )


SUPERVISOR_PROMPT = """Eres el Orquestador Inteligente de Banamex AI Concierge.
Analiza el historial de conversación y decide qué especialista debe responder al último mensaje del usuario:
- `cards_agent`: Todo sobre tarjetas de crédito (Joy, Oro, LineUp, Costco), beneficios, requisitos o comisiones.
- `mortgage_agent`: Todo sobre crédito hipotecario, simulaciones, tasas, plazos (10, 15, 20 años) o preaprobaciones.
- `security_agent`: Todo sobre cargos no reconocidos, movimientos sospechosos, robo/extravío o bloqueo de tarjetas.
- `general_greeting`: Saludos iniciales o temas generales donde debas explicar en qué puedes ayudar.

Si la conversación ya estaba en curso con un especialista (por ejemplo, el usuario confirma un bloqueo o da su correo para una hipoteca), mantén el 
enrutamiento hacia ese mismo especialista.
"""


def input_guardrail_node(state: AgentState) -> dict:
    """Evalúa la seguridad del mensaje entrante antes de procesarlo."""
    last_msg = state["messages"][-1].content
    result = check_input_guardrails(last_msg)

    if not result.is_safe:
        return {
            "messages": [AIMessage(content=result.sanitized_message)],
            "active_agent": f"SecurityGuardrail ({result.reason})",
            "tools_executed": state.get("tools_executed", [])
            + [{"guardrail": "INPUT_BLOCKED", "reason": result.reason}],
        }
    return {}


def route_after_input_guardrail(state: AgentState) -> str:
    """Si el último mensaje ya es una respuesta del guardrail, termina el flujo."""
    if isinstance(state["messages"][-1], AIMessage):
        return END
    return "supervisor"


def supervisor_node(state: AgentState) -> dict:
    """Clasifica la intención y define el siguiente nodo."""
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
    ).with_structured_output(RouteDecision)

    decision: RouteDecision = llm.invoke(
        [SystemMessage(content=SUPERVISOR_PROMPT), *state["messages"][-6:]]
    )
    return {"active_agent": decision.next_agent}


def general_greeting_node(state: AgentState) -> dict:
    """Responde saludos o consultas generales presentando las capacidades del asistente."""
    welcome_text = (
        "¡Hola! Soy tu **Asistente Inteligente de Banamex**. Puedo ayudarte hoy con:\n\n"
        "1. 💳 **Tarjetas de Crédito:** Comparar opciones (*Joy, Oro, LineUp, Costco*), comisiones y elegir la ideal para ti.\n"
        "2. 🏠 **Crédito Hipotecario:** Simular tu mensualidad a 10, 15 o 20 años y registrar tu preaprobación.\n"
        "3. 🛡️ **Centro de Seguridad:** Revisar movimientos recientes, reportar cargos no reconocidos y bloquear tu tarjeta al instante.\n\n"
        "¿Con cuál de estos servicios te gustaría comenzar?"
    )
    return {
        "messages": [AIMessage(content=welcome_text)],
        "active_agent": "Supervisor (Bienvenida)",
    }


def output_guardrail_node(state: AgentState) -> dict:
    """Verifica que la respuesta final cumpla las políticas antifraude del banco."""
    last_ai_msg = state["messages"][-1].content
    result = check_output_guardrails(last_ai_msg)

    if not result.is_safe:
        # Reemplaza el último mensaje inseguro con el mensaje sanitizado
        return {
            "messages": [AIMessage(content=result.sanitized_message, id=state["messages"][-1].id)],
            "active_agent": f"OutputGuardrail ({result.reason})",
        }
    return {}


def build_graph():
    """Construye y compila el grafo multi-agente con persistencia en memoria."""
    workflow = StateGraph(AgentState)

    # Registrar nodos
    workflow.add_node("input_guardrail", input_guardrail_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("cards_agent", cards_agent_node)
    workflow.add_node("mortgage_agent", mortgage_agent_node)
    workflow.add_node("security_agent", security_agent_node)
    workflow.add_node("general_greeting", general_greeting_node)
    workflow.add_node("output_guardrail", output_guardrail_node)

    # Definir flujo de aristas
    workflow.add_edge(START, "input_guardrail")
    workflow.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {END: END, "supervisor": "supervisor"},
    )
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["active_agent"],
        {
            "cards_agent": "cards_agent",
            "mortgage_agent": "mortgage_agent",
            "security_agent": "security_agent",
            "general_greeting": "general_greeting",
        },
    )

    # Todos los especialistas pasan por el filtro de salida antes de responder
    workflow.add_edge("cards_agent", "output_guardrail")
    workflow.add_edge("mortgage_agent", "output_guardrail")
    workflow.add_edge("security_agent", "output_guardrail")
    workflow.add_edge("general_greeting", "output_guardrail")
    workflow.add_edge("output_guardrail", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# Instancia compilada lista para importar en FastAPI
concierge_graph = build_graph()

