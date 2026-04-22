import django
from django.conf import settings
import dj_database_url
import os
import secrets
import uuid
from django.contrib.auth.hashers import make_password

DATABASE_URL = "postgresql://postgres:dCfNTquRUiuSvACGevDoTZVQJWYRuxzS@shinkansen.proxy.rlwy.net:15981/railway"

settings.configure(
    DATABASES={'default': dj_database_url.config(default=DATABASE_URL)},
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes'],
)
django.setup()

from django.db import connection

def setup():
    cnpj = "63693420000110"
    razao = "JR SACOLOES LTDA"
    prefix_hex = secrets.token_hex(4)
    prefix = f"sk_live_{prefix_hex}"
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}.{secret}"
    hashed = make_password(secret)
    id_uuid = uuid.uuid4().hex

    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM fiscal_empresa WHERE cnpj = %s", [cnpj])
        row = cursor.fetchone()
        
        if row:
            cursor.execute(
                "UPDATE fiscal_empresa SET api_key_prefix = %s, api_key_hashed = %s, ativo = TRUE WHERE cnpj = %s",
                [prefix, hashed, cnpj]
            )
            print(f"Atualizada empresa existente: {razao}")
        else:
            cursor.execute(
                "INSERT INTO fiscal_empresa (id, cnpj, razao_social, inscricao_estadual, monitor_url, cloud_client_id, cloud_client_secret, ativo, criado_em, api_key_prefix, api_key_hashed) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)",
                [id_uuid, cnpj, razao, "", "http://localhost:8080", "", "", True, prefix, hashed]
            )
            print(f"Criada nova empresa no Bridge: {razao}")
        
    return full_key

if __name__ == "__main__":
    key = setup()
    print(f"\nCHAVE GERADA (Use no ERP):\n{key}\n")
