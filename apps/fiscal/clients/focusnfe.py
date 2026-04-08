import requests
from django.conf import settings
import structlog

logger = structlog.get_logger()


class FocusNFeClient:
    """
    Cliente base para a API Focus NFe.
    Autenticação: HTTP Basic Auth com token como usuário e senha vazia.
    """

    def __init__(self):
        self.base_url = settings.FOCUSNFE_BASE_URL  # URL muda por ambiente
        self.token = settings.FOCUSNFE_TOKEN
        self.session = requests.Session()
        self.session.auth = (self.token, "")          # senha sempre vazia
        self.session.headers.update({"Content-Type": "application/json"})

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/v2{path}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            logger.info(
                "focusnfe.request",
                method=method,
                path=path,
                status_code=response.status_code,
            )
            return response
        except requests.Timeout:
            logger.error("focusnfe.timeout", method=method, path=path)
            raise
        except requests.ConnectionError:
            logger.error("focusnfe.connection_error", method=method, path=path)
            raise

    def get(self, path: str, params: dict = None) -> requests.Response:
        return self._request("GET", path, params=params)

    def post(self, path: str, data: dict = None, params: dict = None) -> requests.Response:
        return self._request("POST", path, json=data, params=params)

    def delete(self, path: str, data: dict = None) -> requests.Response:
        return self._request("DELETE", path, json=data)

    # Webhooks (Gatilhos)
    def create_hook(self, event: str, url: str) -> requests.Response:
        """Cria um novo gatilho para receber notificações de eventos."""
        payload = {
            "cnpj": settings.FOCUSNFE_CNPJ_EMITENTE,
            "event": event,
            "url": url,
        }
        return self.post("/hooks", data=payload)

    def list_hooks(self) -> requests.Response:
        """Lista todos os gatilhos cadastrados para o token."""
        return self.get("/hooks")

    def delete_hook(self, hook_id: str) -> requests.Response:
        """Exclui um gatilho pelo ID."""
        return self.delete(f"/hooks/{hook_id}")

    # NF-e Recebidas (MDe)
    def get_nfes_recebidas(self, params: dict) -> requests.Response:
        """
        Consulta as notas fiscais emitidas para o CNPJ da empresa.
        Documentação: https://focusnfe.com.br/referencia-api/consultar-nf-e-recebidas/
        """
        return self.get("/nfes_recebidas", params=params)

    def manifestar_nfe(self, chave: str, tipo: str, justificativa: str = None) -> requests.Response:
        """
        Envia a manifestação do destinatário (MDe) para uma NF-e.
        tipo: ciencia, confirmacao, desconhecimento ou nao_realizada.
        """
        payload = {"tipo": tipo}
        if justificativa:
            payload["justificativa"] = justificativa
            
        return self.post(f"/nfes_recebidas/{chave}/manifestar", data=payload)
