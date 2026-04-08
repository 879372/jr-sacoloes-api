# apps/fiscal/services/manifesto_service.py
import xml.etree.ElementTree as ET
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.fiscal.clients.focusnfe import FocusNFeClient
from apps.fiscal.models import NFeRecebida
from apps.compras.models import NotaCompra, ItemNotaCompra
from apps.produtos.models import Produto
import structlog

logger = structlog.get_logger()


class ManifestoService:
    """
    Serviço para manifestação de destinatário (MDe) e gestão de notas recebidas.
    """

    def __init__(self):
        self.client = FocusNFeClient()
        self.cnpj_empresa = settings.FOCUSNFE_CNPJ_EMITENTE

    def sincronizar_notas(self) -> dict:
        """
        Busca novas notas emitidas contra o CNPJ na API da Focus NFe.
        Utiliza o campo 'versao' para buscar apenas atualizações.
        """
        # Busca a maior versão já processada
        ultima_versao = NFeRecebida.objects.order_by('-versao').values_list('versao', flat=True).first() or 0
        
        params = {
            "cnpj": self.cnpj_empresa,
            "versao": ultima_versao
        }
        
        response = self.client.get_nfes_recebidas(params)
        if response.status_code != 200:
            logger.error("fiscal.mde_sync_error", status=response.status_code, text=response.text)
            raise ValueError(f"Erro ao consultar notas recebidas: {response.status_code}")

        notas_data = response.json()
        total_novas = 0
        
        with transaction.atomic():
            for data in notas_data:
                # Criar ou atualizar o registro da nota recebida
                nfe, created = NFeRecebida.objects.update_or_create(
                    chave_nfe=data['chave_nfe'],
                    defaults={
                        'nome_emitente': data['nome_emitente'],
                        'documento_emitente': data['documento_emitente'],
                        'valor_total': Decimal(data['valor_total']),
                        'data_emissao': data['data_emissao'],
                        'situacao': data['situacao'],
                        'manifestacao_destinatario': data.get('manifestacao_destinatario', 'nulo') or 'nulo',
                        'versao': data['versao'],
                        'nfe_completa': data.get('nfe_completa', False)
                    }
                )
                if created:
                    total_novas += 1

        return {
            "total_processadas": len(notas_data),
            "total_novas": total_novas,
            "max_version": response.headers.get("X-Max-Version")
        }

    def manifestar_ciencia(self, nfe_id: str) -> bool:
        """
        Registra a Ciência da Operação para uma nota.
        Isso é necessário para que a SEFAZ libere o XML completo.
        """
        nfe = NFeRecebida.objects.get(id=nfe_id)
        response = self.client.manifestar_nfe(nfe.chave_nfe, "ciencia")
        
        if response.status_code in [200, 201]:
            data = response.json()
            nfe.manifestacao_destinatario = 'ciencia'
            # A Focus pode retornar o XML agora ou via webhook
            if data.get('xml'):
                nfe.xml_completo = data['xml']
                nfe.nfe_completa = True
            nfe.save()
            return True
        
        logger.error("fiscal.mde_manifest_error", chave=nfe.chave_nfe, text=response.text)
        raise ValueError(f"Erro ao manifestar ciência: {response.text}")

    def importar_para_compras(self, nfe_id: str) -> NotaCompra:
        """
        Transforma uma NFeRecebida em uma NotaCompra no ERP.
        Requer que o XML completo esteja disponível.
        """
        nfe_rec = NFeRecebida.objects.get(id=nfe_id)
        
        if nfe_rec.nota_compra:
            return nfe_rec.nota_compra

        # Se não temos o XML completo, tenta baixar agora
        if not nfe_rec.nfe_completa or not nfe_rec.xml_completo:
            response = self.client.get(f"/nfes_recebidas/{nfe_rec.chave_nfe}.xml")
            if response.status_code == 200:
                nfe_rec.xml_completo = response.text
                nfe_rec.nfe_completa = True
                nfe_rec.save()
            else:
                raise ValueError("XML completo ainda não disponível. Certifique-se de que a nota foi manifestada há mais de alguns minutos.")

        # Parse e Importação
        with transaction.atomic():
            nota_compra = self._parse_and_create_compra(nfe_rec)
            nfe_rec.nota_compra = nota_compra
            nfe_rec.save()
            return nota_compra

    def _parse_and_create_compra(self, nfe_rec: NFeRecebida) -> NotaCompra:
        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        root = ET.fromstring(nfe_rec.xml_completo)
        
        if root.tag.endswith("nfeProc"):
            nfe_node = root.find("nfe:NFe", ns)
        else:
            nfe_node = root

        infNfe = nfe_node.find("nfe:infNFe", ns)
        ide = infNfe.find("nfe:ide", ns)
        total = infNfe.find("nfe:total/nfe:ICMSTot", ns)

        numero_nf = ide.find("nfe:nNF", ns).text
        
        nota_compra = NotaCompra.objects.create(
            numero_nf=numero_nf,
            fornecedor=nfe_rec.nome_emitente,
            cnpj_fornecedor=nfe_rec.documento_emitente,
            data_emissao=nfe_rec.data_emissao.date(),
            valor_total=nfe_rec.valor_total,
            chave_acesso=nfe_rec.chave_nfe,
            xml_nfe=nfe_rec.xml_completo,
            status='PENDENTE',
            api_source='Focus NFe MDe'
        )

        # Importar Itens
        for det in infNfe.findall("nfe:det", ns):
            prod = det.find("nfe:prod", ns)
            descricao = prod.find("nfe:xProd", ns).text
            quantidade = Decimal(prod.find("nfe:qCom", ns).text)
            valor_unitario = Decimal(prod.find("nfe:vUnCom", ns).text)
            subtotal = Decimal(prod.find("nfe:vProd", ns).text)

            # Tenta localizar produto pelo nome (simplificado)
            erp_produto = Produto.objects.filter(nome__iexact=descricao).first()

            ItemNotaCompra.objects.create(
                nota=nota_compra,
                produto=erp_produto,
                descricao=descricao,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                subtotal=subtotal
            )

        return nota_compra
