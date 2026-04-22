import django
from django.conf import settings
import dj_database_url
import os

DATABASE_URL = "postgresql://postgres:dCfNTquRUiuSvACGevDoTZVQJWYRuxzS@shinkansen.proxy.rlwy.net:15981/railway"

settings.configure(
    DATABASES={'default': dj_database_url.config(default=DATABASE_URL)},
)
django.setup()

from django.db import connection

def enable_cloud():
    cnpj = "63693420000110"
    client_id = "S0jIawJuH8jPeCikyGH0"
    secret = "HYaP7s4hRDa8M3ErJ3ZX1lfrGKS1aHRX"

    with connection.cursor() as cursor:
        # Verifica se a empresa existe
        cursor.execute("SELECT id FROM fiscal_empresa WHERE cnpj = %s", [cnpj])
        row = cursor.fetchone()
        if not row:
            print(f"Erro: Empresa com CNPJ {cnpj} não encontrada.")
            return

        cursor.execute(
            "UPDATE fiscal_empresa SET cloud_client_id = %s, cloud_client_secret = %s, monitor_url = 'http://localhost:8080' WHERE cnpj = %s",
            [client_id, secret, cnpj]
        )
        print(f"Sucesso! Roteamento Cloud ativado para {cnpj}")

if __name__ == "__main__":
    enable_cloud()
