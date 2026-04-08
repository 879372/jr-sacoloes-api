# apps/fiscal/tests/test_nfce_service.py
import pytest
from unittest.mock import patch, MagicMock
from apps.fiscal.services.nfce_service import NFCeService
from apps.fiscal.models import NFCe, NFCeStatus

PAYLOAD_VALIDO = {
    "data_emissao": "2025-11-19T13:54:31-03:00",
    "items": [
        {
            "numero_item": "1",
            "codigo_ncm": "22030000",
            "codigo_produto": "PROD001",
            "descricao": "CHOPP",
            "quantidade_comercial": 2,
            "quantidade_tributavel": 2,
            "cfop": "5102",
            "valor_unitario_comercial": 12.99,
            "valor_unitario_tributavel": 12.99,
            "valor_bruto": 25.98,
            "unidade_comercial": "UN",
            "unidade_tributavel": "UN",
            "icms_origem": "0",
            "icms_situacao_tributaria": "102",
        }
    ],
    "formas_pagamento": [
        {"forma_pagamento": "01", "valor_pagamento": 25.98}
    ],
}

RESPOSTA_AUTORIZADA = {
    "status": "autorizado",
    "status_sefaz": "100",
    "mensagem_sefaz": "Autorizado o uso da NF-e",
    "chave_nfe": "NFe41190612345678000123650010000000121743484310",
    "numero": "12",
    "serie": "1",
    "caminho_xml_nota_fiscal": "/arquivos/test-nfe.xml",
    "caminho_danfe": "/danfe/test.html",
    "qrcode_url": "http://sefaz.example.com/qrcode",
    "url_consulta_nf": "http://sefaz.example.com/consulta",
}

RESPOSTA_ERRO = {
    "status": "erro_autorizacao",
    "status_sefaz": "704",
    "mensagem_sefaz": "Rejeição: NFC-e com Data-Hora de emissão atrasada",
}


@pytest.mark.django_db
def test_emitir_nfce_autorizada(settings):
    settings.FOCUSNFE_CNPJ_EMITENTE = "12345678000123"

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = RESPOSTA_AUTORIZADA
    
    with patch("apps.fiscal.services.nfce_service.FocusNFeClient") as mock_client:
        mock_client.return_value.post.return_value = mock_response

        service = NFCeService()
        nfce = service.emitir(PAYLOAD_VALIDO)

        assert nfce.status == NFCeStatus.AUTORIZADO
        assert nfce.chave_nfe == "NFe41190612345678000123650010000000121743484310"
        assert nfce.numero == "12"
        assert nfce.foi_autorizada is True


@pytest.mark.django_db
def test_emitir_nfce_erro_autorizacao(settings):
    settings.FOCUSNFE_CNPJ_EMITENTE = "12345678000123"

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = RESPOSTA_ERRO
    
    with patch("apps.fiscal.services.nfce_service.FocusNFeClient") as mock_client:
        mock_client.return_value.post.return_value = mock_response

        service = NFCeService()
        nfce = service.emitir(PAYLOAD_VALIDO)

        assert nfce.status == NFCeStatus.ERRO_AUTORIZACAO
        assert nfce.status_sefaz == "704"
        assert nfce.foi_autorizada is False


@pytest.mark.django_db
def test_cancelar_nfce(settings):
    settings.FOCUSNFE_CNPJ_EMITENTE = "12345678000123"
    from django.utils import timezone

    nfce = NFCe.objects.create(
        ref="testref123",
        cnpj_emitente="12345678000123",
        status=NFCeStatus.AUTORIZADO,
        created_at=timezone.now(),
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "cancelado",
        "status_sefaz": "135",
        "mensagem_sefaz": "Evento registrado e vinculado a NF-e",
        "caminho_xml_cancelamento": "/arquivos/canc.xml",
    }
    
    with patch("apps.fiscal.services.nfce_service.FocusNFeClient") as mock_client:
        mock_client.return_value.delete.return_value = mock_response

        service = NFCeService()
        nfce = service.cancelar(nfce, "Erro no pedido do cliente teste")

        assert nfce.status == NFCeStatus.CANCELADO
        assert nfce.cancelado_em is not None


@pytest.mark.django_db
def test_nfce_nao_pode_cancelar_apos_prazo(settings):
    """NFC-e com mais de 30 minutos não pode ser cancelada."""
    settings.FOCUSNFE_CNPJ_EMITENTE = "12345678000123"
    from django.utils import timezone
    from datetime import timedelta

    nfce = NFCe(
        ref="oldref123",
        cnpj_emitente="12345678000123",
        status=NFCeStatus.AUTORIZADO,
    )
    nfce.created_at = timezone.now() - timedelta(hours=1)

    assert nfce.pode_cancelar is False


@pytest.mark.django_db
def test_enviar_email_mais_de_10_destinatarios(settings):
    settings.FOCUSNFE_CNPJ_EMITENTE = "12345678000123"

    nfce = NFCe(status=NFCeStatus.AUTORIZADO)
    service = NFCeService()

    with pytest.raises(ValueError, match="Máximo de 10"):
        service.enviar_email(nfce, [f"email{i}@test.com" for i in range(11)])
