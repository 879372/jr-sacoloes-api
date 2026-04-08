import requests
from django.conf import settings
from decouple import config

class FocusNFeClient:
    """
    Client para integração com a Focus NFe API.
    A Focus NFe utiliza uma única API para NF-e, NFC-e, etc.
    Documentação: https://focusnfe.com.br/doc/
    """
    
    def __init__(self):
        self.token = config('FOCUS_NFE_TOKEN', default='YOUR_TOKEN_HERE')
        self.enviroment = config('FOCUS_NFE_ENV', default='sandbox') # sandbox ou production
        
        if self.enviroment == 'production':
            self.base_url = "https://api.focusnfe.com.br"
        else:
            self.base_url = "https://homologacao.focusnfe.com.br"

    def _get_url(self, endpoint):
        return f"{self.base_url}{endpoint}"

    def _get_auth(self):
        return (self.token, "")

    def emitir_nfce(self, referencia, dados_nfce):
        """
        Emite uma Nota Fiscal de Consumidor Eletrônica (NFC-e) - Modelo 65.
        referencia: ID único da venda no seu sistema.
        """
        url = self._get_url(f"/v2/nfce?ref={referencia}")
        response = requests.post(url, json=dados_nfce, auth=self._get_auth())
        return response.json()

    def consultar_nfce(self, referencia):
        """Consulta o status de uma NFC-e pela referência."""
        url = self._get_url(f"/v2/nfce/{referencia}")
        response = requests.get(url, auth=self._get_auth())
        return response.json()

    def cancelar_nfce(self, referencia, justificativa):
        """Cancela uma NFC-e emitida."""
        url = self._get_url(f"/v2/nfce/{referencia}")
        data = {"justificativa": justificativa}
        response = requests.delete(url, json=data, auth=self._get_auth())
        return response.json()

    def emitir_nfe(self, referencia, dados_nfe):
        """
        Emite uma Nota Fiscal Eletrônica (NF-e) - Modelo 55.
        """
        url = self._get_url(f"/v2/nfe?ref={referencia}")
        response = requests.post(url, json=dados_nfe, auth=self._get_auth())
        return response.json()
