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

with connection.cursor() as cursor:
    cursor.execute("SELECT cnpj, razao_social FROM fiscal_empresa")
    rows = cursor.fetchall()
    print("Empresas no ACBRAPI:")
    for r in rows:
        print(f"CNPJ: {r[0]} - {r[1]}")
