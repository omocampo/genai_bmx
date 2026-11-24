import re
from pydantic import BaseModel


class GuardrailResult(BaseModel):
    """Resultado de la validación de seguridad."""
    is_safe: bool
    reason: str = ""
    sanitized_message: str = ""


# Patrones comunes de Prompt Injection / Jailbreak
INJECTION_PATTERNS = [
    r"ignora\s+(todas\s+)?(las\s+)?instrucciones",
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"actúa\s+como\s+(un\s+)?(hacker|administrador|sistema)",
    r"muéstrame\s+(tu\s+)?(system\s+prompt|instrucciones\s+internas)",
    r"dame\s+la\s+base\s+de\s+datos",
]

# Patrón para detectar números de tarjeta de 16 dígitos (PCI-DSS compliance)
CARD_NUMBER_PATTERN = r"\b(?:\d[ -]*?){15,16}\b"


def check_input_guardrails(user_message: str) -> GuardrailResult:
    """Evalúa el mensaje del usuario antes de enviarlo a Gemini."""
    text_lower = user_message.lower()

    # 1. Detección de Prompt Injection
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return GuardrailResult(
                is_safe=False,
                reason="PROMPT_INJECTION_DETECTED",
                sanitized_message=(
                    "Por motivos de seguridad bancaria, no puedo procesar esa solicitud. "
                    "¿En qué puedo ayudarte respecto a tarjetas, créditos hipotecarios o aclaraciones?"
                ),
            )

    # 2. Prevención de exposición de datos sensibles (PCI-DSS)
    if re.search(CARD_NUMBER_PATTERN, user_message):
        return GuardrailResult(
            is_safe=False,
            reason="SENSITIVE_DATA_EXPOSURE",
            sanitized_message=(
                "🔒 **Aviso de Seguridad:** Por tu protección, nunca ingreses los 16 dígitos de tu tarjeta, "
                "tu CVV ni tu NIP en este chat. Para revisar tus movimientos, solo necesitamos tu ID de cliente "
                "(ej. `CUST-1001`)."
            ),
        )

    return GuardrailResult(is_safe=True, sanitized_message=user_message)


def check_output_guardrails(ai_response: str) -> GuardrailResult:
    """Valida que la respuesta del modelo cumpla con las reglas antifraude del banco."""
    forbidden_requests = [
        r"ingresa\s+tu\s+(nip|cvv|contraseña|netkey)",
        r"compárteme\s+tu\s+(nip|cvv|código\s+sms)",
        r"dime\s+los\s+16\s+dígitos",
    ]

    response_lower = ai_response.lower()
    for pattern in forbidden_requests:
        if re.search(pattern, response_lower):
            return GuardrailResult(
                is_safe=False,
                reason="POLICY_VIOLATION_OUTPUT",
                sanitized_message=(
                    "Lo siento, por seguridad nunca te solicitaré claves, NIP, CVV ni códigos NetKey. "
                    "Por favor, continúa tu trámite de forma segura o comunícate a la línea oficial Banamex."
                ),
            )

    return GuardrailResult(is_safe=True, sanitized_message=ai_response)

