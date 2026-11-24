from typing import Any, Optional
import psycopg
from psycopg.rows import dict_row
from src.config import settings


def get_connection():
    """Abre una conexión a PostgreSQL retornando filas como diccionarios."""
    return psycopg.connect(settings.postgres_psycopg_uri, row_factory=dict_row)


def get_customer_by_id(customer_id: str) -> Optional[dict[str, Any]]:
    """Obtiene el perfil de un cliente por su ID."""
    query = "SELECT * FROM customers WHERE customer_id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id,))
            return cur.fetchone()


def get_recent_transactions(customer_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Lista las transacciones recientes de un cliente."""
    query = """
        SELECT tx_id, merchant, amount, tx_date, location, is_disputed, dispute_folio
        FROM transactions
        WHERE customer_id = %s
        ORDER BY tx_date DESC
        LIMIT %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id, limit))
            return cur.fetchall()


def report_fraud_and_block_card(customer_id: str, tx_id: str, folio: str) -> bool:
    """Marca una transacción como disputada y bloquea preventivamente la tarjeta."""
    update_tx = """
        UPDATE transactions
        SET is_disputed = TRUE, dispute_folio = %s
        WHERE tx_id = %s AND customer_id = %s;
    """
    update_card = """
        UPDATE customers
        SET card_status = 'BLOCKED_FRAUD'
        WHERE customer_id = %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(update_tx, (folio, tx_id, customer_id))
            if cur.rowcount == 0:
                return False
            cur.execute(update_card, (customer_id,))
        conn.commit()
    return True


def save_mortgage_lead(
    customer_name: str,
    contact_email: str,
    property_value: float,
    down_payment: float,
    loan_amount: float,
    term_years: int,
    estimated_monthly_payment: float,
) -> int:
    """Guarda una solicitud de preaprobación hipotecaria y devuelve el ID generado."""
    query = """
        INSERT INTO mortgage_leads (
            customer_name, contact_email, property_value, down_payment,
            loan_amount, term_years, estimated_monthly_payment
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING lead_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    customer_name,
                    contact_email,
                    property_value,
                    down_payment,
                    loan_amount,
                    term_years,
                    estimated_monthly_payment,
                ),
            )
            result = cur.fetchone()
        conn.commit()
    return result["lead_id"]


def get_all_mortgage_leads() -> list[dict[str, Any]]:
    """Consulta los leads guardados (útil para el panel de observabilidad en Streamlit)."""
    query = "SELECT * FROM mortgage_leads ORDER BY created_at DESC LIMIT 10;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

