from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from apps.fiscal.models import NFe, NFCe, NFeStatus, NFCeStatus
import structlog

logger = structlog.get_logger()

@method_decorator(csrf_exempt, name='dispatch')
class FocusNFeWebhookView(APIView):
    """
    Recebe notificações de eventos da Focus NFe (Gatilhos/Webhooks).
    """
    permission_classes = [] # Aberto para receber da Focus NFe (pode-se adicionar validação de IP ou Token no futuro)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        ref = data.get("ref") or request.query_params.get("ref")
        event = data.get("event")
        
        logger.info("focusnfe.webhook_received", ref=ref, event=event, status=data.get("status"))

        if not ref:
            return Response({"erro": "Referência não informada"}, status=status.HTTP_400_BAD_REQUEST)

        # Tenta localizar como NF-e (Modelo 55)
        nfe = NFe.objects.filter(ref=ref).first()
        if nfe:
            self._atualizar_nfe(nfe, data)
            return Response({"status": "ok", "tipo": "nfe"})

        # Tenta localizar como NFC-e (Modelo 65)
        nfce = NFCe.objects.filter(ref=ref).first()
        if nfce:
            self._atualizar_nfce(nfce, data)
            return Response({"status": "ok", "tipo": "nfce"})

        logger.warning("focusnfe.webhook_ref_not_found", ref=ref)
        return Response({"erro": "Referência não encontrada no sistema"}, status=status.HTTP_404_NOT_FOUND)

    def _atualizar_nfe(self, nfe, data):
        from apps.fiscal.services.nfe_service import NFeService
        service = NFeService()
        service._atualizar_nfe_com_resposta(nfe, data)
        nfe.save()
        logger.info("focusnfe.webhook_nfe_updated", ref=nfe.ref, status=nfe.status)

    def _atualizar_nfce(self, nfce, data):
        from apps.fiscal.services.nfce_service import NFCeService
        service = NFCeService()
        service._atualizar_nfce_com_resposta(nfce, data)
        nfce.save()
        logger.info("focusnfe.webhook_nfce_updated", ref=nfce.ref, status=nfce.status)
