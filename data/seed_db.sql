-- Habilitar extensión vectorial para RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Tabla de Clientes Simulados
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    monthly_income NUMERIC(12, 2) NOT NULL,
    credit_score INT NOT NULL,
    card_type VARCHAR(50) NOT NULL,
    card_last_four VARCHAR(4) NOT NULL,
    card_status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE | BLOCKED_FRAUD
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Transacciones (Para el Agente de Seguridad / Cargos No Reconocidos)
CREATE TABLE IF NOT EXISTS transactions (
    tx_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) REFERENCES customers(customer_id),
    merchant VARCHAR(100) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    tx_date TIMESTAMP NOT NULL,
    location VARCHAR(100) NOT NULL,
    is_disputed BOOLEAN DEFAULT FALSE,
    dispute_folio VARCHAR(30)
);

-- 3. Tabla de Solicitudes / Leads Hipotecarios (Para el Agente Hipotecario)
CREATE TABLE IF NOT EXISTS mortgage_leads (
    lead_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100) NOT NULL,
    property_value NUMERIC(14, 2) NOT NULL,
    down_payment NUMERIC(14, 2) NOT NULL,
    loan_amount NUMERIC(14, 2) NOT NULL,
    term_years INT NOT NULL,
    estimated_monthly_payment NUMERIC(12, 2) NOT NULL,
    status VARCHAR(30) DEFAULT 'PRE_APPROVED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- DATOS DE PRUEBA (Para el reclutador)
-- ==========================================
INSERT INTO customers (customer_id, full_name, email, monthly_income, credit_score, card_type, card_last_four, card_status)
VALUES 
    ('CUST-1001', 'Carlos Mendoza', 'carlos.mendoza@ejemplo.com', 35000.00, 720, 'Tarjeta Oro Banamex', '4821', 'ACTIVE'),
    ('CUST-1002', 'Sofía Ramírez', 'sofia.ramirez@ejemplo.com', 18500.00, 685, 'Tarjeta Joy Banamex', '9034', 'ACTIVE')
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO transactions (tx_id, customer_id, merchant, amount, tx_date, location, is_disputed)
VALUES 
    ('TX-901', 'CUST-1001', 'Supermercado La Comer', 1450.50, NOW() - INTERVAL '2 days', 'CDMX, México', FALSE),
    ('TX-902', 'CUST-1001', 'Tienda Electrónica Online HK', 18900.00, NOW() - INTERVAL '3 hours', 'Hong Kong (Online)', FALSE),
    ('TX-903', 'CUST-1002', 'Cafetería Centro', 125.00, NOW() - INTERVAL '1 day', 'Guadalajara, México', FALSE),
    ('TX-904', 'CUST-1002', 'Transferencia Casino Internacional', 9500.00, NOW() - INTERVAL '1 hour', 'Desconocida (Online)', FALSE)
ON CONFLICT (tx_id) DO NOTHING;

