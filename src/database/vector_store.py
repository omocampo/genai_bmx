from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from src.config import settings

COLLECTION_NAME = "banamex_credit_cards"


def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Inicializa el modelo de embeddings de Google Gemini."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
    )


def get_vector_store() -> PGVector:
    """Retorna la instancia conectada a PostgreSQL + pgvector."""
    embeddings = get_embeddings_model()
    return PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=settings.postgres_sqlalchemy_uri,
        use_jsonb=True,
    )

