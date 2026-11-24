import json
import uuid
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState
from src.config import settings
from src.database.postgres import (
    get_customer_by_id,
    get_recent_transactions,
    report_fraud_and_block_card,
)


@tool
def check_customer_transactions(customer_id: str) -> str:
    """Consulta el perfil y los últimos movimientos de un cliente usando su ID (ej. CUST-1001)."""
    customer = get_customer_by_id(customer_id.strip().upper())
    if not customer:
        return json.dumps({
            "error": f"No se encontró ningún cliente con el ID '{customer_id}'. Usa CUST-1001 o CUST-1002 para pruebas."
        })

    txs = get_recent_transactions(customer["customer_id"])
    # Convertir fechas/decimales a strings serializables
    serialized_txs = [
        {
            "tx_id": tx["tx_id"],
            "merchant": tx["merchant"],
            "amount_mxn": float(tx["amount"]),
            "date": tx["tx_date"].strftime("%Y-%m-%d %H:%M"),
            "location": tx["location"],
            "is_disputed": tx["is_disputed"],
            "dispute_folio": tx["dispute_folio"],
        }
        for tx in txs
    ]

    return json.dumps({
        "customer_name": customer["full_name"],
        "card_type": customer["card_type"],
        "card_last_four": customer["card_last_four"],
        "card_status": customer["card_status"],
        "recent_transactions": serialized_txs,
    })


@tool
def block_card_and_create_dispute(customer_id: str, tx_id: str) -> str:
    """Bloquea preventivamente la tarjeta del cliente y levanta un folio por cargo no reconocido."""
    folio = f"ACL-{uuid.uuid4().hex[:6].upper()}"
    success = report_fraud_and_block_card(
        customer_id=customer_id.strip().upper(),
        tx_id=tx_id.strip().upper(),
        folio=folio,
    )
    if not success:
        return json.dumps({
            "error": "No fue posible procesar el bloqueo. Verifica que el ID de cliente y de transacción sean correctos."
        })

    return json.dumps({
        "status": "CARD_BLOCKED_AND_DISPUTE_OPENED",
        "dispute_folio": folio,
        "tx_id": tx_id.upper(),
        "action_taken": "Tarjeta bloqueada preventivamente y bonificación temporal iniciada (48 hrs hábiles).",
    })


SECURITY_SYSTEM_PROMPT = """Eres el Especialista del Centro de Seguridad y Ayuda Urgente de Banamex.
Atiendes reportes de cargos no reconocidos, robo o extravío de tarjeta con máxima empatía, rapidez y rigor de seguridad.

REGLAS ESTRICTAS DE SEGURIDAD:
1. JAMÁS pidas los 16 dígitos de la tarjeta, NIP, CVV, contraseñas ni códigos NetKey.
2. Para revisar movimientos, solicita únicamente el ID de cliente (si el usuario no lo ha dado, indícale que para esta demo puede usar `CUST-1001` o 
`CUST-1002`).
3. Muestra los movimientos recientes encontrados con `check_customer_transactions` (incluyendo comercio, monto, fecha y ubicación) y pregunta cuál cargo 
no reconoce.
4. ANTES de ejecutar `block_card_and_create_dispute`, pide confirmación explícita al cliente indicando que su tarjeta será bloqueada por seguridad.
5. Una vez confirmado, ejecuta el bloqueo y entrega su folio de aclaración (`ACL-...`) de forma clara.
"""


def security_agent_node(state: AgentState) -> dict:
    """Nodo de LangGraph para el especialista de Seguridad y Fraudes."""
    tools = [check_customer_transactions, block_card_and_create_dispute]
    tools_by_name = {t.name: t for t in tools}

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,  # Temperatura 0 para máximo rigor operativo
    ).bind_tools(tools)

    # Si hay un customer_id preseleccionado en la UI, lo inyectamos como contexto
    context_note = ""
    if state.get("customer_id"):
        context_note = f"\n[Contexto del sistema: El cliente autenticado en sesión es {state['customer_id']}]"

    messages = [
        SystemMessage(content=SECURITY_SYSTEM_PROMPT + context_note),
        *state["messages"],
    ]
    executed_logs = list(state.get("tools_executed", []))

    response = llm.invoke(messages)
    new_messages = [response]

    while response.tool_calls:
        for tool_call in response.tool_calls:
            tool_fn = tools_by_name[tool_call["name"]]
            tool_result = tool_fn.invoke(tool_call["args"])

            executed_logs.append({
                "agent": "SecurityAgent",
                "tool": tool_call["name"],
                "args": tool_call["args"],
                "result": json.loads(tool_result),
            })

            new_messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"],
                )
            )
        response = llm.invoke(messages + new_messages)
        new_messages.append(response)

    return {
        "messages": [AIMessage(content=response.content)],
        "active_agent": "SecurityAgent (Fraudes & Guardrails)",
        "tools_executed": executed_logs,
    }

