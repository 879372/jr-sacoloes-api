import django
from django.conf import settings
import dj_database_url
import os

DATABASE_URL = "postgresql://postgres:dCfNTquRUiuSvACGevDoTZVQJWYRuxzS@shinkansen.proxy.rlwy.net:15981/railway"

settings.configure(
    DATABASES={'default': dj_database_url.config(default=DATABASE_URL)},
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes'],
)
django.setup()

from django.db import connection

# Mock de empresa para o serviço
class MockEmpresa:
    def __init__(self, client_id, secret):
        self.cloud_client_id = client_id
        self.cloud_client_secret = secret
        self.razao_social = "Teste"

def test_auth():
    client_id = "S0jIawJuH8jPeCikyGH0"
    secret = "HYaP7s4hRDa8M3ErJ3ZX1lfrGKS1aHRX"
    
    # Importação dinâmica para usar o diretório do ACBRAPI
    import sys
    sys.path.append("/Users/josekaio/Documents/ACBRAPI")
    from apps.fiscal.services.acbr_cloud_service import AcbrCloudService
    
    empresa = MockEmpresa(client_id, secret)
    svc = AcbrCloudService(empresa=empresa)
    
    try:
        token = svc._get_token()
        print(f"Sucesso! Token obtido: {token[:20]}...")
    except Exception as e:
        print(f"Erro na autenticação Cloud: {str(e)}")

if __name__ == "__main__":
    test_auth()
