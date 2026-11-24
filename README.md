# 🏦 BMX AI Concierge — Sistema Multi-Agente Bancario

[![CI - Tests & AI Quality Gate](https://github.com)](https://github.com)

Asistente financiero inteligente de arquitectura multi-agente diseñado para optimizar la experiencia de clientes y procesos internos en banca retail, 
impulsado por **Google Gemini 2.5 Flash**, **LangGraph**, **FastAPI** y **PostgreSQL (`pgvector`)**.

🔗 **[Probar Demo en Vivo Aquí](https://streamlit.app)** *(Incluye panel de observabilidad en tiempo real)*

---

## 🎯 Casos de Uso Implementados

1. **💳 Perfilador y Asesor de Tarjetas de Crédito (RAG + Structured Outputs):**
   - Indexación semántica del catálogo oficial (*Joy, Oro, LineUp, Costco*) mediante `gemini-embedding-001` y `pgvector`.
   - Extracción estructurada del perfil financiero con **Pydantic** y recomendación fundamentada citando CAT y anualidades reales.
2. **🏠 Simulador de Crédito Hipotecario y CRM (*Tool Calling* + SQL):**
   - Cálculo determinista de tablas de amortización a 10, 15 y 20 años mediante herramientas en Python (cero alucinaciones matemáticas).
   - Persistencia automática de solicitudes de preaprobación (`leads`) en PostgreSQL.
3. **🛡️ Centro de Seguridad y Cargos No Reconocidos (*Guardrails* + Transacciones SQL):**
   - Consulta de movimientos sospechosos, bloqueo preventivo de tarjeta y generación de folios de aclaración (`ACL-XXXXXX`).
   - Doble capa de seguridad (*Input/Output Guardrails*) contra *Prompt Injection* y exposición de datos sensibles (PCI-DSS: bloqueo de tarjetas de 16 
dígitos, NIP y CVV).

## 🏗️ Arquitectura

- **Orquestación:** LangGraph (Patrón Supervisor con memoria conversacional por sesión).
- **Modelos IA:** Google `gemini-2.5-flash` (razonamiento y *function calling*) + `gemini-embedding-001` (vectores).
- **Backend & Validación:** FastAPI + Pydantic v2.
- **Datos:** PostgreSQL 16 + `pgvector` (almacenamiento híbrido relacional y vectorial).
- **Calidad & CI/CD:** Pruebas unitarias con `pytest`, evaluación *LLM-as-a-Judge* y GitHub Actions.

## 🚀 Ejecución Local Rápida

```bash
# 1. Clonar e instalar dependencias
git clone https://github.com
cd bmx-ai-concierge
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configurar variables de entorno
cp .env.example .env  # Agrega tu GEMINI_API_KEY

# 3. Levantar PostgreSQL + pgvector e indexar catálogo
docker compose up -d
python3 scripts/ingest_docs.py

# 4. Iniciar Backend y Frontend
uvicorn src.api.main:app --reload
streamlit run src/ui/app.py
```

