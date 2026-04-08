# apps/fiscal/exceptions.py
from rest_framework.exceptions import APIException
from rest_framework import status


class NFCeEmissaoError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "nfce_emissao_error"

    def __init__(self, mensagem_sefaz: str, status_sefaz: str = None):
        self.detail = {
            "erro": True,
            "codigo": self.default_code,
            "mensagem": mensagem_sefaz,
            "status_sefaz": status_sefaz,
        }


class NFCeCancelamentoError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "nfce_cancelamento_error"


class NFCeNaoEncontrada(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "nfce_nao_encontrada"
