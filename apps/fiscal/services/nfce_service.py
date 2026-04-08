# apps/fiscal/services/nfce_service.py
import uuid
from django.conf import settings
from django.utils import timezone

from apps.fiscal.clients.focusnfe import FocusNFeClient
from apps.fiscal.models import NFCe, NFCeStatus
from apps.fiscal.mappers import venda_to_focus_nfe
from apps.vendas.models import Venda
import structlog

logger = structlog.get_logger()


class NFCeService:
    """
    Camada de serviço para emissão e gestão de NFC-e via Focus NFe.
    Todos os processos são síncronos: a resposta já traz autorizado ou erro.
    """

    def __init__(self):
        self.client = FocusNFeClient()
        self.cnpj_emitente = settings.FOCUSNFE_CNPJ_EMITENTE

    def _gerar_ref(self) -> str:
        """
        Gera ref alfanumérica única sem caracteres especiais.
        """
        return uuid.uuid4().hex

    def _montar_payload(self, dados: dict) -> dict:
        return {
            "cnpj_emitente": self.cnpj_emitente,
            "data_emissao": dados["data_emissao"],
            "presenca_comprador": dados.get("presenca_comprador", "1"),
            "modalidade_frete": dados.get("modalidade_frete", "9"),
            "local_destino": dados.get("local_destino", "1"),
            "natureza_operacao": dados.get("natureza_operacao", "VENDA AO CONSUMIDOR"),
            "nome_destinatario": dados.get("nome_destinatario"),
            "cpf_destinatario": dados.get("cpf_destinatario"),
            "cnpj_destinatario": dados.get("cnpj_destinatario"),
            "indicador_inscricao_estadual_destinatario": dados.get("indicador_inscricao_estadual_destinatario", "9"),
            "informacoes_adicionais_contribuinte": dados.get("info_adicional"),
            "items": dados["items"],
            "formas_pagamento": dados["formas_pagamento"],
        }

    def emitir(self, dados: dict) -> NFCe:
        ref = self._gerar_ref()
        payload = self._montar_payload(dados)

        logger.info("nfce.emitindo", ref=ref, cnpj=self.cnpj_emitente)

        nfce = NFCe.objects.create(
            ref=ref,
            cnpj_emitente=self.cnpj_emitente,
            status=NFCeStatus.PENDENTE,
            payload_enviado=payload,
        )

        try:
            response = self.client.post("/nfce", data=payload, params={"ref": ref})
            data = response.json()
            nfce.resposta_focusnfe = data

            if response.status_code == 201:
                self._atualizar_nfce_com_resposta(nfce, data)
            else:
                nfce.status = NFCeStatus.ERRO_AUTORIZACAO
                nfce.mensagem_sefaz = data.get("mensagem", "Erro desconhecido")
                logger.error("nfce.erro_emissao", ref=ref, data=data)

        except Exception as exc:
            nfce.status = NFCeStatus.ERRO_AUTORIZACAO
            nfce.mensagem_sefaz = str(exc)
            logger.error("nfce.excecao_emissao", ref=ref, error=str(exc))

        nfce.save()
        return nfce

    def emitir_from_venda(self, venda_id: int) -> NFCe:
        """
        Gera o payload a partir de uma Venda e emite a NFC-e.
        """
        venda = Venda.objects.get(pk=venda_id)
        dados = venda_to_focus_nfe(venda)
        
        nfce = self.emitir(dados)
        nfce.venda = venda
        nfce.save()
        
        return nfce

    def _atualizar_nfce_com_resposta(self, nfce: NFCe, data: dict) -> None:
        status_map = {
            "autorizado": NFCeStatus.AUTORIZADO,
            "erro_autorizacao": NFCeStatus.ERRO_AUTORIZACAO,
            "denegado": NFCeStatus.DENEGADO,
        }

        nfce.status = status_map.get(data.get("status"), NFCeStatus.ERRO_AUTORIZACAO)
        nfce.status_sefaz = data.get("status_sefaz")
        nfce.mensagem_sefaz = data.get("mensagem_sefaz")
        nfce.chave_nfe = data.get("chave_nfe")
        nfce.numero = data.get("numero")
        nfce.serie = data.get("serie")
        nfce.caminho_xml = data.get("caminho_xml_nota_fiscal")
        nfce.caminho_danfe = data.get("caminho_danfe")
        nfce.qrcode_url = data.get("qrcode_url")
        nfce.url_consulta_nf = data.get("url_consulta_nf")
        nfce.contingencia_offline = data.get("contingencia_offline", False)
        nfce.contingencia_offline_efetivada = data.get("contingencia_offline_efetivada", False)

    def consultar(self, ref: str, completa: bool = False) -> dict:
        params = {"completa": 1 if completa else 0}
        response = self.client.get(f"/nfce/{ref}", params=params)

        if response.status_code == 404:
            raise NFCe.DoesNotExist(f"NFC-e com ref={ref} não encontrada na Focus NFe.")

        return response.json()

    def cancelar(self, nfce: NFCe, justificativa: str) -> NFCe:
        if not nfce.pode_cancelar:
            raise ValueError(
                "NFC-e não pode ser cancelada. Verifique se está autorizada e dentro do prazo de 30 minutos."
            )

        if len(justificativa) < 15 or len(justificativa) > 255:
            raise ValueError("Justificativa deve ter entre 15 e 255 caracteres.")

        logger.info("nfce.cancelando", ref=nfce.ref, chave=nfce.chave_nfe)

        response = self.client.delete(f"/nfce/{nfce.ref}", data={"justificativa": justificativa})
        data = response.json()

        if response.status_code == 200 and data.get("status") == "cancelado":
            nfce.status = NFCeStatus.CANCELADO
            nfce.status_sefaz = data.get("status_sefaz")
            nfce.mensagem_sefaz = data.get("mensagem_sefaz")
            nfce.caminho_xml_cancelamento = data.get("caminho_xml_cancelamento")
            nfce.justificativa_cancelamento = justificativa
            nfce.cancelado_em = timezone.now()
            nfce.save()
            logger.info("nfce.cancelada", ref=nfce.ref)
        else:
            logger.error("nfce.erro_cancelamento", ref=nfce.ref, data=data)
            raise ValueError(data.get("mensagem", "Erro ao cancelar NFC-e."))

        return nfce

    def enviar_email(self, nfce: NFCe, emails: list[str]) -> bool:
        if not nfce.foi_autorizada:
            raise ValueError("Só é possível enviar e-mail de NFC-e autorizada.")

        if len(emails) > 10:
            raise ValueError("Máximo de 10 e-mails por requisição.")

        response = self.client.post(f"/nfce/{nfce.ref}/email", data={"emails": emails})

        if response.status_code == 200:
            logger.info("nfce.email_agendado", ref=nfce.ref, emails=emails)
            return True

        data = response.json()
        logger.error("nfce.erro_email", ref=nfce.ref, data=data)
        raise ValueError(data.get("mensagem", "Erro ao agendar envio de e-mail."))

    def inutilizar(self, serie: str, numero_inicial: str, numero_final: str, justificativa: str) -> dict:
        payload = {
            "cnpj": self.cnpj_emitente,
            "serie": serie,
            "numero_inicial": numero_inicial,
            "numero_final": numero_final,
            "justificativa": justificativa,
        }
        logger.warning(
            "nfce.inutilizando",
            serie=serie,
            numero_inicial=numero_inicial,
            numero_final=numero_final,
        )
        response = self.client.post("/nfce/inutilizacao", data=payload)
        return response.json()

    def consultar_inutilizacoes(self, data_inicial: str = None, data_final: str = None, numero_inicial: int = None, numero_final: int = None) -> list[dict]:
        params = {"cnpj": self.cnpj_emitente}
        if data_inicial: params["data_recebimento_inicial"] = data_inicial
        if data_final: params["data_recebimento_final"] = data_final
        if numero_inicial: params["numero_inicial"] = numero_inicial
        if numero_final: params["numero_final"] = numero_final

        response = self.client.get("/nfce/inutilizacoes", params=params)
        return response.json()
