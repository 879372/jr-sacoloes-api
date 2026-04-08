# apps/fiscal/constants.py

# Status retornados pela Focus NFe -> status interno Antigravity
STATUS_FOCUSNFE_MAP = {
    "autorizado": "autorizado",
    "erro_autorizacao": "erro_autorizacao",
    "cancelado": "cancelado",
    "denegado": "denegado",
    "processando_autorizacao": "pendente",
}

# Códigos SEFAZ comuns
SEFAZ_STATUS = {
    "100": "Autorizado o uso da NF-e",
    "135": "Evento registrado e vinculado a NF-e",          # cancelamento
    "150": "Autorizado o uso da NF-e, autorização fora de prazo",
    "204": "Duplicidade de NF-e",
    "301": "Uso denegado: Irregularidade fiscal do emitente",
    "302": "Uso denegado: Irregularidade fiscal do destinatário",
    "704": "Rejeição: NFC-e com Data-Hora de emissão atrasada",
    "241": "Rejeição: Um número da faixa já foi utilizado",
}

# Formas de pagamento
FORMAS_PAGAMENTO = {
    "01": "Dinheiro",
    "02": "Cheque",
    "03": "Cartão de Crédito",
    "04": "Cartão de Débito",
    "05": "Crédito Loja",
    "10": "Vale Alimentação",
    "11": "Vale Refeição",
    "12": "Vale Presente",
    "13": "Vale Combustível",
    "99": "Outros",
}

# Presença do comprador
PRESENCA_COMPRADOR = {
    "0": "Não se aplica",
    "1": "Operação presencial",
    "2": "Operação não presencial — pela Internet",
    "3": "Operação não presencial — Teleatendimento",
    "4": "NFC-e em entrega a domicílio",
    "9": "Operação não presencial — Outros",
}
