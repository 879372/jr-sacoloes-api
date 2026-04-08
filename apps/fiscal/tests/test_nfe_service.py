# apps/fiscal/tests/test_nfe_service.py
import pytest
from unittest.mock import patch, MagicMock
from apps.fiscal.services.nfe_service import NFeService
from apps.fiscal.models import NFe, NFeStatus

PAYLOAD_VALIDO = {
    "natureza_operacao": "Venda de mercadoria",
    "data_emissao": "2025-11-19T13:54:31-03:00",
    "items": [{"descricao": "Teste", "quantidade_comercial": 1, "valor_unitario_comercial": 10}],
    "formas_pagamento": [{"forma_pagamento": "01", "valor_pagamento": 10}],
}

@pytest.mark.django_db
def test_emitir_nfe_autorizada(settings):
    settings.FOCUSNFE_CNPJ_EMITENTE = "12345678000123"

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "autorizado",
        "chave_nfe": "NFe551234567890",
        "numero": "1",
        "serie": "1"
    }
    
    with patch("apps.fiscal.services.nfe_service.FocusNFeClient") as mock_client:
        mock_client.return_value.post.return_value = mock_response

        service = NFeService()
        nfe = service.emitir(PAYLOAD_VALIDO)

        assert nfe.status == NFeStatus.AUTORIZADO
        assert nfe.chave_nfe == "NFe551234567890"

@pytest.mark.django_db
def test_importar_xml_manifesto():
    from apps.fiscal.services.manifesto_service import ManifestoService
    from apps.compras.models import NotaCompra
    
    xml_mock = """<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <NFe>
            <infNFe Id="NFe3512345" versao="4.00">
                <ide><nNF>123</nNF><dhEmi>2025-01-01T10:00:00-03:00</dhEmi></ide>
                <emit><CNPJ>11122233000144</CNPJ><xNome>Fornecedor Teste</xNome></emit>
                <det nItem="1">
                    <prod>
                        <cProd>001</cProd><xProd>Produto Teste</xProd>
                        <qCom>10.000</qCom><vUnCom>5.00</vUnCom><vProd>50.00</vProd>
                    </prod>
                </det>
                <total><ICMSTot><vNF>50.00</vNF></ICMSTot></total>
            </infNFe>
        </NFe>
    </nfeProc>"""
    
    service = ManifestoService()
    nota = service.importar_xml(xml_mock, "3512345")
    
    assert nota.numero_nf == "123"
    assert nota.fornecedor == "Fornecedor Teste"
    assert nota.itens.count() == 1
    assert nota.itens.first().subtotal == 50
