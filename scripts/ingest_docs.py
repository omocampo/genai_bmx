import sys
from pathlib import Path

# Asegurar que Python encuentre el paquete 'src' al ejecutar desde la raíz
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from langchain_text_splitters import MarkdownHeaderTextSplitter
from src.database.vector_store import get_vector_store


def ingest_credit_cards() -> None:
    """Lee el catálogo Markdown de tarjetas, lo divide por sección y lo sube a pgvector."""
    doc_path = ROOT_DIR / "data" / "raw_docs" / "tarjetas_banamex.md"

    if not doc_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo en: {doc_path}")

    print(f"📄 Leyendo catálogo desde: {doc_path}")
    markdown_text = doc_path.read_text(encoding="utf-8")

    # Dividir por encabezados H1 y H2 para mantener intacta la ficha de cada tarjeta
    headers_to_split_on = [
        ("#", "categoria"),
        ("##", "producto"),
    ]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    docs = splitter.split_text(markdown_text)

    # Enriquecer metadatos para trazabilidad en el panel de observabilidad
    for idx, doc in enumerate(docs):
        doc.metadata["source"] = "tarjetas_banamex.md"
        doc.metadata["chunk_id"] = idx + 1

    print(f"🧩 Fragmentos generados: {len(docs)}")
    for d in docs:
        print(f"   - {d.metadata.get('producto', 'General')}")

    print("🚀 Generando embeddings con Gemini e indexando en pgvector...")
    vector_store = get_vector_store()

    # Limpiar colección previa si existía para evitar duplicados al re-ejecutar
    vector_store.delete_collection()
    vector_store.create_collection()
    vector_store.add_documents(docs)

    print("✅ ¡Ingesta completada con éxito! El conocimiento RAG está listo en PostgreSQL.")


if __name__ == "__main__":
    ingest_credit_cards()

