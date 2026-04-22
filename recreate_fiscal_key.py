import os
import secrets
import django
from django.conf import settings
from django.contrib.auth.hashers import make_password
import dj_database_url

# Configuração mínima do Django para usar o make_password e DB
DATABASE_URL = "postgresql://postgres:dCfNTquRUiuSvACGevDoTZVQJWYRuxzS@shinkansen.proxy.rlwy.net:15981/railway"

settings.configure(
    DATABASES={'default': dj_database_url.config(default=DATABASE_URL)},
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes'],
)
django.setup()

from django.db import connection

def create_key(cnpj):
    prefix_hex = secrets.token_hex(4)
    prefix = f"sk_live_{prefix_hex}"
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}.{secret}"
    hashed = make_password(secret)

    with connection.cursor() as cursor:
        # Verifica se a empresa existe
        cursor.execute("SELECT id FROM fiscal_empresa WHERE cnpj = %s", [cnpj])
        row = cursor.fetchone()
        if not row:
            print(f"Erro: Empresa com CNPJ {cnpj} não encontrada no banco do ACBRAPI.")
            return None
        
        empresa_id = row[0]
        # Atualiza a chave
        cursor.execute(
            "UPDATE fiscal_empresa SET api_key_prefix = %s, api_key_hashed = %s, ativo = TRUE WHERE id = %s",
            [prefix, hashed, empresa_id]
        )
        print(f"Sucesso! Nova chave gerada para CNPJ {cnpj}")
        return full_key

if __name__ == "__main__":
    key = create_key("63693420000110")
    if key:
        print(f"\nNOVA CHAVE FISCAL (Copie e guarde):\n{key}\n")
