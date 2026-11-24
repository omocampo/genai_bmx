import json
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState
from src.config import settings
from src.database.postgres import save_mortgage_lead


@tool
def calculate_mortgage_plan(
    property_value: float,
    down_payment: float,
    term_years: int = 15,
) -> str:
    """Calcula la mensualidad estimada de un Crédito Hipotecario Banamex.
    
    Args:
        property_value: Valor total de la vivienda en MXN (mínimo $500,000).
        down_payment: Monto del enganche en MXN (mínimo 10% del valor de la vivienda).
        term_years: Plazo del crédito en años (opciones válidas: 10, 15 o 20).
    """
    if term_years not in (10, 15, 20):
        return json.dumps({"error": "El plazo debe ser exactamente 10, 15 o 20 años."})
    if property_value < 500_000:
        return json.dumps({"error": "El valor mínimo de la vivienda es de $500,000 MXN."})
    if down_payment < property_value * 0.10:
        return json.dumps({
            "error": f"El enganche mínimo es del 10% (${property_value * 0.10:,.2f} MXN)."
        })

    loan_amount = property_value - down_payment
    annual_rate = 0.1045  # Tasa anual fija referencial 10.45%
    monthly_rate = annual_rate / 12
    total_months = term_years * 12

    # Fórmula estándar de amortización francesa
    monthly_payment = loan_amount * (
        (monthly_rate * (1 + monthly_rate) ** total_months)
        / ((1 + monthly_rate) ** total_months - 1)
    )
    recommended_income = monthly_payment * 2.5  # Regla prudencial: pago <= 40% del ingreso

    return json.dumps({
        "property_value_mxn": round(property_value, 2),
        "down_payment_mxn": round(down_payment, 2),
        "loan_amount_mxn": round(loan_amount, 2),
        "term_years": term_years,
        "annual_interest_rate": "10.45%",
        "estimated_monthly_payment_mxn": round(monthly_payment, 2),
        "recommended_monthly_income_mxn": round(recommended_income, 2),
    })


@tool
def register_mortgage_preapproval(
    customer_name: str,
    contact_email: str,
    property_value: float,
    down_payment: float,
    term_years: int,
    estimated_monthly_payment: float,
) -> str:
    """Registra una solicitud de preaprobación hipotecaria en la base de datos CRM del banco."""
    loan_amount = property_value - down_payment
    lead_id = save_mortgage_lead(
        customer_name=customer_name,
        contact_email=contact_email,
        property_value=property_value,
        down_payment=down_payment,
        loan_amount=loan_amount,
        term_years=term_years,
        estimated_monthly_payment=estimated_monthly_payment,
    )
    return json.dumps({
        "status": "PRE_APPROVED_REGISTERED",
        "lead_id": f"HIP-{lead_id:04d}",
        "message": "Solicitud guardada exitosamente en el sistema hipotecario Banamex.",
    })


MORTGAGE_SYSTEM_PROMPT = """Eres el Especialista en Crédito Hipotecario de Banamex.
Ayudas a los clientes a simular su crédito hipotecario a plazos de 10, 15 o 20 años y a registrar su solicitud de preaprobación.

REGLAS:
1. NUNCA calcules mensualidades por tu cuenta; usa siempre la herramienta `calculate_mortgage_plan`.
2. Si el usuario quiere simular pero le falta algún dato (valor de vivienda, enganche o plazo de 10/15/20 años), pídeselo de forma clara.
3. Después de mostrar una simulación, ofrece registrar su preaprobación pidiendo su nombre completo y correo electrónico para ejecutar 
`register_mortgage_preapproval`.
4. Presenta las cifras financieras con formato claro ($ MXN) y recuerda que son cálculos informativos sujetos a avalúo y estudio de crédito.
"""


def mortgage_agent_node(state: AgentState) -> dict:
    """Nodo de LangGraph para el especialista de Crédito Hipotecario."""
    tools = [calculate_mortgage_plan, register_mortgage_preapproval]
    tools_by_name = {t.name: t for t in tools}

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,
    ).bind_tools(tools)

    messages = [SystemMessage(content=MORTGAGE_SYSTEM_PROMPT), *state["messages"]]
    executed_logs = list(state.get("tools_executed", []))

    # Bucle de ejecución de herramientas (ReAct loop)
    response = llm.invoke(messages)
    new_messages = [response]

    while response.tool_calls:
        for tool_call in response.tool_calls:
            tool_fn = tools_by_name[tool_call["name"]]
            tool_result = tool_fn.invoke(tool_call["args"])

            executed_logs.append({
                "agent": "MortgageAgent",
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
        "active_agent": "MortgageAgent (Hipotecas & SQL CRM)",
        "tools_executed": executed_logs,
    }

