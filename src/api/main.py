from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

from src.agents.graph import concierge_graph
from src.api.schemas import ChatRequest, ChatResponse
from src.config import settings
from src.database.postgres import (
    get_all_mortgage_leads,
    get_customer_by_id,
    get_recent_transactions,
)

app = FastAPI(
    title="Banamex AI Concierge API",
    description="API Multi-Agente para atención bancaria inteligente con Gemini 2.5 Flash y LangGraph.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Endpoint de monitoreo de salud del servicio."""
    return {
        "status": "healthy",
        "model": settings.gemini_model,
        "environment": settings.environment,
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """Procesa un turno de conversación a través del grafo multi-agente."""
    try:
        config = {"configurable": {"thread_id": payload.session_id}}

        # Reiniciamos los logs por turno para mostrar solo lo ocurrido en esta interacción
        initial_input = {
            "messages": [HumanMessage(content=payload.message)],
            "customer_id": payload.customer_id,
            "tools_executed": [],
            "retrieved_docs": [],
        }

        final_state = concierge_graph.invoke(initial_input, config=config)
        last_message = final_state["messages"][-1].content

        return ChatResponse(
            session_id=payload.session_id,
            reply=last_message,
            active_agent=final_state.get("active_agent", "Unknown"),
            tools_executed=final_state.get("tools_executed", []),
            retrieved_docs=final_state.get("retrieved_docs", []),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en el motor de IA: {str(exc)}")


@app.get("/api/v1/observability/db-state")
def get_db_observability():
    """Expone el estado en vivo de PostgreSQL para el panel de demostración."""
    try:
        c1 = get_customer_by_id("CUST-1001")
        c2 = get_customer_by_id("CUST-1002")
        txs_c1 = get_recent_transactions("CUST-1001", limit=3)
        leads = get_all_mortgage_leads()
        return {
            "customers": [c for c in (c1, c2) if c],
            "recent_transactions_cust_1001": txs_c1,
            "mortgage_leads": leads,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error consultando DB: {str(exc)}")

