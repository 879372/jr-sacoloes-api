# apps/fiscal/services/nfe_service.py
import uuid
from django.conf import settings
from django.utils import timezone

from apps.fiscal.clients.focusnfe import FocusNFeClient
from apps.fiscal.models import NFe, NFeStatus
from apps.fiscal.mappers import venda_to_focus_nfe_modelo_55
from apps.vendas.models import Venda
import structlog

logger = structlog.get_logger()


class NFeService:
    """
    Camada de serviço para emissão e gestão de NF-e (Modelo 55) via Focus NFe.
    """

    def __init__(self):
        self.client = FocusNFeClient()
        self.cnpj_emitente = settings.FOCUSNFE_CNPJ_EMITENTE

    def _gerar_ref(self) -> str:
        return uuid.uuid4().hex

    def emitir(self, dados: dict, ref: str = None) -> NFe:
        if not ref:
            ref = self._gerar_ref()
            
        logger.info("nfe.emitindo", ref=ref, cnpj=self.cnpj_emitente)

        nfe = NFe.objects.create(
            ref=ref,
            cnpj_emitente=self.cnpj_emitente,
            status=NFeStatus.PENDENTE,
            natureza_operacao=dados.get("natureza_operacao", "Venda de mercadoria"),
            tipo_documento=dados.get("tipo_documento", 1),
            finalidade_emissao=dados.get("finalidade_emissao", 1),
            cnpj_destinatario=dados.get("cnpj_destinatario"),
            cpf_destinatario=dados.get("cpf_destinatario"),
            nome_destinatario=dados.get("nome_destinatario"),
            valor_total=dados.get("valor_total"),
            payload_enviado=dados,
        )

        try:
            # Para NF-e (Modelo 55), o endpoint é /nfe
            response = self.client.post("/nfe", data=dados, params={"ref": ref})
            data = response.json()
            nfe.resposta_focusnfe = data

            if response.status_code in [201, 202, 200]:
                self._atualizar_nfe_com_resposta(nfe, data)
            else:
                nfe.status = NFeStatus.ERRO_AUTORIZACAO
                nfe.mensagem_sefaz = data.get("mensagem", "Erro desconhecido")
                logger.error("nfe.erro_emissao", ref=ref, data=data)

        except Exception as exc:
            nfe.status = NFeStatus.ERRO_AUTORIZACAO
            nfe.mensagem_sefaz = str(exc)
            logger.error("nfe.excecao_emissao", ref=ref, error=str(exc))

        nfe.save()
        return nfe

    def emitir_from_venda(self, venda_id: int, natureza_operacao: str = "Venda de mercadoria") -> NFe:
        """
        Gera o payload a partir de uma Venda e emite a NF-e.
        """
        venda = Venda.objects.get(pk=venda_id)
        dados = venda_to_focus_nfe_modelo_55(venda, natureza_operacao=natureza_operacao)
        
        nfe = self.emitir(dados)
        nfe.venda = venda
        nfe.save()
        
        return nfe

    def _atualizar_nfe_com_resposta(self, nfe: NFe, data: dict) -> None:
        status_map = {
            "autorizado": NFeStatus.AUTORIZADO,
            "processando_autorizacao": NFeStatus.PROCESSANDO,
            "erro_autorizacao": NFeStatus.ERRO_AUTORIZACAO,
            "denegado": NFeStatus.DENEGADO,
            "cancelado": NFeStatus.CANCELADO,
        }

        nfe.status = status_map.get(data.get("status"), NFeStatus.ERRO_AUTORIZACAO)
        nfe.status_sefaz = data.get("status_sefaz")
        nfe.mensagem_sefaz = data.get("mensagem_sefaz")
        nfe.chave_nfe = data.get("chave_nfe")
        nfe.numero = data.get("numero")
        nfe.serie = data.get("serie")
        nfe.protocolo = data.get("protocolo")
        nfe.caminho_xml = data.get("caminho_xml_nota_fiscal")
        nfe.caminho_danfe = data.get("caminho_danfe")

    def consultar(self, ref: str) -> dict:
        response = self.client.get(f"/nfe/{ref}")
        return response.json()

    def sincronizar_status(self, nfe: NFe) -> NFe:
        """
        Consulta a Focus NFe e atualiza o status local.
        """
        data = self.consultar(nfe.ref)
        self._atualizar_nfe_com_resposta(nfe, data)
        nfe.tentativas_consulta += 1
        nfe.ultima_consulta_em = timezone.now()
        nfe.save()
        return nfe

    def cancelar(self, nfe: NFe, justificativa: str) -> NFe:
        if not nfe.foi_autorizada:
            raise ValueError("Apenas notas autorizadas podem ser canceladas.")

        response = self.client.delete(f"/nfe/{nfe.ref}", data={"justificativa": justificativa})
        data = response.json()

        if response.status_code == 200 and data.get("status") == "cancelado":
            nfe.status = NFeStatus.CANCELADO
            nfe.status_sefaz = data.get("status_sefaz")
            nfe.mensagem_sefaz = data.get("mensagem_sefaz")
            nfe.caminho_xml_cancelamento = data.get("caminho_xml_cancelamento")
            nfe.justificativa_cancelamento = justificativa
            nfe.cancelado_em = timezone.now()
            nfe.save()
        else:
            raise ValueError(data.get("mensagem", "Erro ao cancelar NF-e."))

        return nfe

    def enviar_email(self, nfe: NFe, emails: list) -> bool:
        """Envia a NF-e por e-mail via Focus NFe."""
        if not nfe.foi_autorizada:
            raise ValueError("Só é possível enviar e-mail de NF-e autorizada.")
        
        response = self.client.post(f"/nfe/{nfe.ref}/email", data={"emails": emails})
        return response.status_code == 200

    def gerar_danfe_preview(self, payload: dict) -> bytes:
        """Gera o PDF de pré-visualização (sem valor fiscal)."""
        # Note: Focus NFe endpoint for preview is sometimes /nfe/danfe via POST raw
        # Using a dedicated method in client for this if needed, but here we use the session directly
        url = f"{settings.FOCUSNFE_BASE_URL}/v2/nfe/danfe"
        response = self.client.session.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.content
        raise ValueError("Erro ao gerar pré-visualização do DANFe.")

    def reconciliar_nfes_pendentes(self):
        """Reconcilia notas que estão em processamento há algum tempo."""
        pendentes = NFe.objects.filter(
            status__in=[NFeStatus.PENDENTE, NFeStatus.PROCESSANDO]
        ).exclude(tentativas_consulta__gt=20)
        
        for nfe in pendentes:
            try:
                self.sincronizar_status(nfe)
            except Exception as e:
                logger.error("nfe.reconciliar_erro", ref=nfe.ref, error=str(e))
